import os
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# MongoDB + Auth
from pymongo import MongoClient
from passlib.context import CryptContext
from jose import JWTError, jwt

# Config
if "OPENAI_API_KEY" not in os.environ:
    print("WARNING: OPENAI_API_KEY environment variable not set. Chat functionality will fail.")
else:
    print("OPENAI_API_KEY is set")

MONGODB_URI = os.environ.get("MONGODB_URI")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

def get_db():
    if not MONGODB_URI:
        return None
    client = MongoClient(MONGODB_URI)
    return client.get_default_database()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"id": user_id, "email": email}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# --- Lazy loading: Initialize RAG components on first use ---
rag_chain = None

def get_rag_chain():
    global rag_chain
    if rag_chain is None:
        print("Loading RAG model and vector store...")
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.load_local(
            "faiss_index", 
            embeddings, 
            allow_dangerous_deserialization=True 
        )
        retriever = vectorstore.as_retriever()
        
        # RAG Prompt template
        template = """Use the following pieces of context to answer the question.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context: {context}

Question: {question}

Helpful Answer: """
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # LLM model
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        
        # RAG Chain using LCEL
        def format_docs(docs):
            return "\n\n".join([d.page_content for d in docs])
        
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        print("✅ RAG Application is ready.")
    return rag_chain

app = FastAPI()

class Query(BaseModel):
    question: str

class SignUp(BaseModel):
    email: str
    password: str

class ChatSave(BaseModel):
    question: str
    answer: str = ""
    error: str = ""

@app.get("/health")
def read_root():
    return {"message": "BEE EDU RAG Application is live!", "version": "v1"}

@app.get("/")
@app.get("/ui")
def ui():
    ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "index.html")
    return FileResponse(ui_path)

@app.post("/auth/signup")
def auth_signup(body: SignUp):
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    users = db["users"]
    existing = users.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = pwd_context.hash(body.password)
    doc = {"email": body.email, "password": hashed, "createdAt": datetime.utcnow()}
    result = users.insert_one(doc)
    user_id = str(result.inserted_id)
    token = create_access_token({"sub": user_id, "email": body.email})
    return {"token": token, "user": {"id": user_id, "email": body.email}}

class Login(BaseModel):
    email: str
    password: str

@app.post("/auth/login")
def auth_login(body: Login):
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    users = db["users"]
    user = users.find_one({"email": body.email})
    if not user or not pwd_context.verify(body.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user_id = str(user["_id"])
    token = create_access_token({"sub": user_id, "email": user["email"]})
    return {"token": token, "user": {"id": user_id, "email": user["email"]}}

@app.get("/auth/me")
def auth_me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"]}

@app.post("/chats")
def chats_save(body: ChatSave, user: dict = Depends(get_current_user)):
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    db["chats"].insert_one({
        "userId": user["id"],
        "question": body.question,
        "answer": body.answer,
        "error": body.error,
        "createdAt": datetime.utcnow()
    })
    return {"ok": True}

@app.get("/chats")
def chats_list(user: dict = Depends(get_current_user)):
    db = get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")
    cursor = db["chats"].find({"userId": user["id"]}).sort("createdAt", 1).limit(100)
    items = []
    for doc in cursor:
        items.append({
            "question": doc.get("question", ""),
            "answer": doc.get("answer", ""),
            "error": doc.get("error", ""),
            "createdAt": doc.get("createdAt").isoformat() if doc.get("createdAt") else None
        })
    return {"chats": items}

@app.post("/chat")
def chat(query: Query):
    try:
        # Lazy load RAG chain on first use
        chain = get_rag_chain()
        answer = chain.invoke(query.question)
        return {"answer": f"Helpful Answer: V5 {answer}"}
    except Exception as e:
        # Return error message
        return {"error": str(e)}, 500

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
