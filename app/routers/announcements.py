from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.announcement import Announcement as AnnouncementModel, AnnouncementRead, AnnouncementType
from app.models.user import User as UserModel, Role
from app.routers.users import get_current_user
from app.schemas import announcement as announcement_schema

router = APIRouter()


@router.get("/me", response_model=List[announcement_schema.AnnouncementWithReadStatus])
def get_my_announcements(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    unread_only: bool = Query(False, description="Filter to show only unread announcements"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get announcements for the current user (both broadcast and personal).
    """
    # Get all announcements that are either:
    # 1. Broadcast announcements (recipient_id is None)
    # 2. Personal announcements (recipient_id == current_user.id)
    query = db.query(AnnouncementModel).filter(
        or_(
            AnnouncementModel.recipient_id == None,  # Broadcast
            AnnouncementModel.recipient_id == current_user.id  # Personal
        )
    ).order_by(AnnouncementModel.created_at.desc())
    
    announcements = query.offset(skip).limit(limit).all()
    
    # Get read status for each announcement
    result = []
    for ann in announcements:
        read_record = db.query(AnnouncementRead).filter(
            AnnouncementRead.announcement_id == ann.id,
            AnnouncementRead.user_id == current_user.id
        ).first()
        
        read_status = read_record is not None
        
        # Filter by unread if requested
        if unread_only and read_status:
            continue
        
        ann_dict = {
            "id": ann.id,
            "title": ann.title,
            "message": ann.message,
            "type": ann.type,
            "recipient_id": ann.recipient_id,
            "created_by_id": ann.created_by_id,
            "created_at": ann.created_at,
            "read": read_status,
            "read_at": read_record.read_at if read_record else None
        }
        result.append(ann_dict)
    
    return result


@router.post("/me/{announcement_id}/mark-read", status_code=status.HTTP_200_OK)
def mark_announcement_read(
    announcement_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark an announcement as read for the current user.
    """
    # Check if announcement exists and is accessible by user
    announcement = db.query(AnnouncementModel).filter(
        AnnouncementModel.id == announcement_id,
        or_(
            AnnouncementModel.recipient_id == None,
            AnnouncementModel.recipient_id == current_user.id
        )
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    # Check if already read
    existing_read = db.query(AnnouncementRead).filter(
        AnnouncementRead.announcement_id == announcement_id,
        AnnouncementRead.user_id == current_user.id
    ).first()
    
    if existing_read:
        return {"message": "Announcement already marked as read"}
    
    # Create read record
    read_record = AnnouncementRead(
        announcement_id=announcement_id,
        user_id=current_user.id,
        read_at=datetime.utcnow()
    )
    db.add(read_record)
    db.commit()
    
    return {"message": "Announcement marked as read"}


@router.delete("/me/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement_for_user(
    announcement_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete the read record for an announcement (removes it from user's view).
    Note: This doesn't delete the announcement itself, just removes it from user's list.
    """
    announcement = db.query(AnnouncementModel).filter(
        AnnouncementModel.id == announcement_id,
        or_(
            AnnouncementModel.recipient_id == None,
            AnnouncementModel.recipient_id == current_user.id
        )
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    # Delete read record if exists
    read_record = db.query(AnnouncementRead).filter(
        AnnouncementRead.announcement_id == announcement_id,
        AnnouncementRead.user_id == current_user.id
    ).first()
    
    if read_record:
        db.delete(read_record)
        db.commit()
    
    # For personal announcements, we can actually delete them
    if announcement.recipient_id == current_user.id:
        db.delete(announcement)
        db.commit()
    
    return None


@router.get("/", response_model=List[announcement_schema.Announcement])
def get_all_announcements(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    recipient_id: Optional[int] = Query(None, description="Filter by recipient ID"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all announcements (admin only).
    """
    # Only admins can see all announcements
    if current_user.role not in [Role.ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    query = db.query(AnnouncementModel)
    
    if recipient_id is not None:
        query = query.filter(AnnouncementModel.recipient_id == recipient_id)
    
    announcements = query.order_by(AnnouncementModel.created_at.desc()).offset(skip).limit(limit).all()
    return announcements


@router.post("/", response_model=announcement_schema.Announcement)
def create_announcement(
    announcement: announcement_schema.AnnouncementCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new announcement (admin only).
    """
    # Only admins can create announcements
    if current_user.role not in [Role.ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create announcements"
        )
    
    db_announcement = AnnouncementModel(
        title=announcement.title,
        message=announcement.message,
        type=announcement.type.value if isinstance(announcement.type, AnnouncementType) else announcement.type,
        recipient_id=announcement.recipient_id,
        created_by_id=current_user.id,
        created_at=datetime.utcnow()
    )
    
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    
    return db_announcement


@router.put("/{announcement_id}", response_model=announcement_schema.Announcement)
def update_announcement(
    announcement_id: int,
    announcement: announcement_schema.AnnouncementUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an announcement (admin only).
    """
    # Only admins can update announcements
    if current_user.role not in [Role.ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update announcements"
        )
    
    db_announcement = db.query(AnnouncementModel).filter(
        AnnouncementModel.id == announcement_id
    ).first()
    
    if not db_announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    # Update fields if provided
    update_data = announcement.model_dump(exclude_unset=True)
    
    if 'title' in update_data:
        db_announcement.title = update_data['title']
    if 'message' in update_data:
        db_announcement.message = update_data['message']
    if 'type' in update_data:
        type_value = update_data['type']
        db_announcement.type = type_value.value if isinstance(type_value, AnnouncementType) else type_value
    if 'recipient_id' in update_data:
        db_announcement.recipient_id = update_data['recipient_id']
    
    db.commit()
    db.refresh(db_announcement)
    
    return db_announcement


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an announcement (admin only).
    """
    # Only admins can delete announcements
    if current_user.role not in [Role.ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete announcements"
        )
    
    db_announcement = db.query(AnnouncementModel).filter(
        AnnouncementModel.id == announcement_id
    ).first()
    
    if not db_announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    # Delete all read records for this announcement
    db.query(AnnouncementRead).filter(
        AnnouncementRead.announcement_id == announcement_id
    ).delete()
    
    # Delete the announcement
    db.delete(db_announcement)
    db.commit()
    
    return None


@router.post("/feedback", status_code=status.HTTP_200_OK)
def send_feedback(
    feedback: announcement_schema.FeedbackCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send feedback to admin. Creates an announcement that only admins can see.
    """
    # Find an admin user to send feedback to
    admin = db.query(UserModel).filter(
        UserModel.role.in_([Role.ADMIN, Role.SUPERADMIN]),
        UserModel.is_active == True
    ).first()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No active admin found"
        )
    
    # Create announcement from user to admin
    # Use the enum value explicitly to ensure correct serialization to database
    feedback_announcement = AnnouncementModel(
        title=f"Feedback from {current_user.name or current_user.email}",
        message=feedback.message,
        type=AnnouncementType.INFO.value,  # Use .value to get "info" string
        recipient_id=admin.id,  # Send to first available admin
        created_by_id=current_user.id,
        created_at=datetime.utcnow()
    )
    
    db.add(feedback_announcement)
    db.commit()
    db.refresh(feedback_announcement)
    
    return {"message": "Feedback sent successfully"}

