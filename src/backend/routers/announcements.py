"""
Announcement management endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime
from bson.objectid import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("/")
def get_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (not expired)"""
    now = datetime.now()
    
    # Find announcements where:
    # - expiration_date is in the future, AND
    # - start_date is either None or in the past
    announcements = list(announcements_collection.find({
        "$and": [
            {"expiration_date": {"$gte": now}},
            {"$or": [
                {"start_date": None},
                {"start_date": {"$lte": now}}
            ]}
        ]
    }).sort("created_at", -1))
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        announcement["_id"] = str(announcement["_id"])
        if announcement.get("start_date"):
            announcement["start_date"] = announcement["start_date"].isoformat()
        if announcement.get("expiration_date"):
            announcement["expiration_date"] = announcement["expiration_date"].isoformat()
        if announcement.get("created_at"):
            announcement["created_at"] = announcement["created_at"].isoformat()
    
    return announcements


@router.get("/all")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements (for management) - only for signed in users"""
    # Check if user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    announcements = list(announcements_collection.find().sort("created_at", -1))
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        announcement["_id"] = str(announcement["_id"])
        if announcement.get("start_date"):
            announcement["start_date"] = announcement["start_date"].isoformat()
        if announcement.get("expiration_date"):
            announcement["expiration_date"] = announcement["expiration_date"].isoformat()
        if announcement.get("created_at"):
            announcement["created_at"] = announcement["created_at"].isoformat()
    
    return announcements


@router.post("/")
def create_announcement(
    username: str,
    title: str,
    message: str,
    expiration_date: str,
    start_date: str = None
) -> Dict[str, Any]:
    """Create a new announcement - only for signed in users"""
    # Check if user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Parse dates
    try:
        exp_date = datetime.fromisoformat(expiration_date)
        start = datetime.fromisoformat(start_date) if start_date else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    # Validate expiration_date is in the future
    if exp_date <= datetime.now():
        raise HTTPException(status_code=400, detail="Expiration date must be in the future")
    
    # Validate start_date is before expiration_date
    if start and start >= exp_date:
        raise HTTPException(status_code=400, detail="Start date must be before expiration date")
    
    announcement = {
        "_id": ObjectId(),
        "title": title,
        "message": message,
        "start_date": start,
        "expiration_date": exp_date,
        "created_by": username,
        "created_at": datetime.now()
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = str(result.inserted_id)
    
    # Convert dates to ISO format
    if announcement.get("start_date"):
        announcement["start_date"] = announcement["start_date"].isoformat()
    announcement["expiration_date"] = announcement["expiration_date"].isoformat()
    announcement["created_at"] = announcement["created_at"].isoformat()
    
    return announcement


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    username: str,
    title: str = None,
    message: str = None,
    expiration_date: str = None,
    start_date: str = None
) -> Dict[str, Any]:
    """Update an announcement - only for signed in users"""
    # Check if user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Find the announcement
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    announcement = announcements_collection.find_one({"_id": obj_id})
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Build update document
    update_doc = {}
    if title is not None:
        update_doc["title"] = title
    if message is not None:
        update_doc["message"] = message
    
    if expiration_date is not None:
        try:
            exp_date = datetime.fromisoformat(expiration_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        # Validate expiration_date is in the future
        if exp_date <= datetime.now():
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")
        
        update_doc["expiration_date"] = exp_date
    
    if start_date is not None:
        if start_date == "":
            update_doc["start_date"] = None
        else:
            try:
                start = datetime.fromisoformat(start_date)
                update_doc["start_date"] = start
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    # Validate start_date is before expiration_date if both are present
    exp = update_doc.get("expiration_date", announcement.get("expiration_date"))
    st = update_doc.get("start_date", announcement.get("start_date"))
    if st and exp and st >= exp:
        raise HTTPException(status_code=400, detail="Start date must be before expiration date")
    
    # Update the announcement
    announcements_collection.update_one({"_id": obj_id}, {"$set": update_doc})
    
    # Return updated announcement
    updated = announcements_collection.find_one({"_id": obj_id})
    updated["_id"] = str(updated["_id"])
    
    if updated.get("start_date"):
        updated["start_date"] = updated["start_date"].isoformat()
    if updated.get("expiration_date"):
        updated["expiration_date"] = updated["expiration_date"].isoformat()
    if updated.get("created_at"):
        updated["created_at"] = updated["created_at"].isoformat()
    
    return updated


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, Any]:
    """Delete an announcement - only for signed in users"""
    # Check if user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Find and delete the announcement
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
