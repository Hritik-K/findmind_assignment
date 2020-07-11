#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  8 13:59:59 2020
@author: Hritik
"""

from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer

from typing import Optional, List
from pydantic import BaseModel
from bson.objectid import ObjectId

import motor.motor_asyncio

import json

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

client = motor.motor_asyncio.AsyncIOMotorClient()
db = client.todo
tasks = db.tasks
users = db.users

class Task(BaseModel):
    name: str
    due_date: str
    update: Optional[str]

    def to_dict(self):
        return { 'name': self.name, 'due_date':  self.due_date}

class User(BaseModel):
    username: str
    password: str
    tasks: List[Task] = []

@app.post("/signup")
async def add_new_user(user: User):
    document = {"username": user.username, "password": user.password}
    check_username = users.find_one({"username": user.username})
    if(check_username != None):
        return "Sorry! that username already exists. Please try another username"
    if(len(user.username) <= 3):
        return "username should have more than 3 characters"
    if(user.username.isnumeric()):
        return "username should not have all numbers"
    if(len(user.password) <= 7):
        return "password should have more than 7 characters"
    users.insert_one(document)
    return "You are registered now. Please log in"

@app.get("/login")
async def login(user: User):
    return user

@app.get("/task")
async def show_tasks(token:str = Depends(oauth2_scheme)):
    cursor = tasks.find({})
    result = []
    for doc in await cursor.to_list(length=10):
        doc["_id"] = str(doc["_id"])
        result.append(doc)
    return result

@app.get("/task/{task_id}")
async def show_task(task_id: str):
    cursor = await tasks.find_one({"_id": ObjectId(task_id)})
    if(cursor is None):
        return "Task with task_id: " + task_id + " does not exist"
    cursor["_id"] = str(cursor["_id"])
    return cursor

@app.post("/task")
async def create_task(task: Task):
    document = {"name": task.name, "due_date": task.due_date}
    result = await tasks.insert_one(document)
    if(result.acknowledged):
        return json.dumps(task.to_dict())

@app.put("/task/{task_id}")
async def update_task(task_id: str, task_update: dict):
    document = await tasks.update_one({"_id": ObjectId(task_id)},
                                      {"$set": task_update})
    if(document is None):
        return "Task " + task_id + " does not exist"
    if(document.acknowledged == False):
        return "Could not update task: " + task_id
    return document.raw_result

@app.delete("/task/{task_id}")
async def delete_task(task_id: str):
    result = await tasks.delete_one({ "_id": ObjectId(task_id) })
    print(result.raw_result["n"])
    if(result.raw_result["n"] == 0):
        return "Task with task_id: " + task_id + " does not exist"
    return "Task " + task_id + " deleted"

