#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  8 13:59:59 2020
@author: Hritik
"""

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from typing import Optional, List
from pydantic import BaseModel
from bson.objectid import ObjectId

import motor.motor_asyncio

import json
from datetime import datetime, timedelta

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

client = motor.motor_asyncio.AsyncIOMotorClient()
db = client.todo
tasks = db.tasks
users = db.users

SECRET_KEY = "3505f571a441230b55d16acf57bc52f6c42eba9c4e68d74bf37712a7db740281"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Task(BaseModel):
    name: str
    due_date: str
    update: Optional[str]
    owner: Optional[str] = "" #will be string of ObjectId
    shared_to: Optional[List[str]] = []   #will be list of string of ObjectId's & are tasks shared with user

class User(BaseModel):
    username: str
    password: str

class User_in_db(User):
    username: str
    hashed_password: str
    own_tasks: Optional[List[str]] = []
    tasks_shared: Optional[List[str]] = []

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

async def authenticate_user( username: str, password: str):
    user = await users.find_one({"username": username})
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = await users.find_one({"username": username})
    if user is None:
        raise credentials_exception
    return user

@app.post("/signup")
async def add_new_user(user: User):
    check_username = await users.find_one({"username": user.username})
    if(check_username != None):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="This username already exists",
        )
    if(len(user.username) <= 3):
        raise HTTPException(
            status_code=status.HTTP_417_EXPECTATION_FAILED,
            detail="Username should contain more than 3 characters",
        )
    if(user.username.isnumeric()):
        raise HTTPException(
            status_code=status.HTTP_417_EXPECTATION_FAILED,
            detail="Username should not have all numbers",
        )
    if(len(user.password) <= 7):
        raise HTTPException(
            status_code=status.HTTP_417_EXPECTATION_FAILED,
            detail="Password should contain more than 7 characters",
        )
    document = {"username": user.username, "hashed_password": hash_password(user.password), "own_tasks": [], "shared_tasks": []}
    users.insert_one(document)
    return "You are registered now. Please log in"

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password
    user = await authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# @app.post("/login", response_model=Token)
# async def login(form_data: OAuth2PasswordRequestForm = Depends()):
#     username = form_data.username
#     password = form_data.password
#     user = await authenticate_user(username, password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user["username"]}, expires_delta=access_token_expires
#     )
#     return {"access_token": access_token, "token_type": "bearer"}

@app.get("/tasks")
async def show_tasks(token:str = Depends(oauth2_scheme)):
    user = await get_current_user(token)
    cursor = tasks.find({"owner": (user["_id"])})
    result = []
    for doc in await cursor.to_list(length=10):
        doc["_id"] = str(doc["_id"])
        result.append(doc)
    return result

@app.get("/tasks/{task_id}")
async def show_task(task_id: str, token:str = Depends(oauth2_scheme)):
    user = await get_current_user(token)
    if task_id in user["own_tasks"] or task_id in user["tasks_shared"]:
        cursor = await tasks.find_one({"_id": ObjectId(task_id)})
        if(cursor is None):
            return "Task with task_id: " + task_id + " does not exist"
        cursor["_id"] = str(cursor["_id"])
        return cursor
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have access to view this task",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.post("/tasks")
async def create_task(task: Task, token:str = Depends(oauth2_scheme)):
    user = await get_current_user(token)
    document = {"name": task.name, "due_date": task.due_date, "owner": str(user["_id"])}
    result = await tasks.insert_one(document)
    if not result.acknowledged:
        return "Could not add task"
    my_tasks = user["own_tasks"].append(str(result.inserted_id))
    users.update_one({"_id": user["_id"]}, {"$set": {"own_tasks": my_tasks}})
    return "Task added"

@app.put("/tasks/{task_id}")
async def update_task(task_id: str, task_update: dict, token:str = Depends(oauth2_scheme)):
    user = await get_current_user(token)
    if task_id not in user["own_tasks"] or task_id not in user["shared_to"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have access to this task",
            headers={"WWW-Authenticate": "Bearer"},
        )
    document = await tasks.update_one({"_id": ObjectId(task_id)},
                                      {"$set": task_update})
    if(document is None):
        return "Task " + task_id + " does not exist"
    if(document.acknowledged == False):
        return "Could not update task: " + task_id
    return document.raw_result


@app.delete("/task/{task_id}")
async def delete_task(task_id: str, token:str = Depends(oauth2_scheme)):
    user = await get_current_user(token)
    if task_id not in user["own_tasks"] or task_id not in user["shared_to"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have access to this task",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await tasks.delete_one({ "_id": ObjectId(task_id) })
    if(result.raw_result["n"] == 0):
        return "Task with task_id: " + task_id + " does not exist"
    return "Task " + task_id + " deleted"

