import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User as UserModel
from app.routers.users import get_current_user
from pydantic import BaseModel

router = APIRouter()

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class DocumentResponse(BaseModel):
    id: str
    type: str
    file_name: str
    file_url: str
    status: str
    uploaded_at: str
    reviewed_at: Optional[str] = None


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document for the current doctor.
    document_type: 'professional-card', 'selfie-wallet', or 'proof-of-residence'
    """
    # Validate document type
    valid_types = ['professional-card', 'selfie-wallet', 'proof-of-residence']
    if document_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content to check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)}MB"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}{file_ext}"
    file_path = UPLOAD_DIR / file_name
    
    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Store document reference in user's attached_document field
    # For now, we'll store as JSON string. In production, consider a separate documents table
    import json
    from datetime import datetime
    
    # Get user from current session to avoid session issues
    db_user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get existing documents
    existing_docs = []
    if db_user.attached_document:
        try:
            existing_docs = json.loads(db_user.attached_document)
            if isinstance(existing_docs, dict):
                existing_docs = [existing_docs]
        except (json.JSONDecodeError, TypeError):
            existing_docs = []
    
    # Remove existing document of same type
    existing_docs = [doc for doc in existing_docs if doc.get("type") != document_type]
    
    # Add new document
    document_data = {
        "id": file_id,
        "type": document_type,
        "file_name": file.filename,
        "file_path": str(file_path),
        "file_url": f"/documents/{file_name}",
        "uploaded_at": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    existing_docs.append(document_data)
    
    # Update user's attached_document field
    db_user.attached_document = json.dumps(existing_docs)
    db.commit()
    db.refresh(db_user)
    
    return DocumentResponse(
        id=file_id,
        type=document_type,
        file_name=file.filename,
        file_url=f"/documents/{file_name}",
        status="pending",
        uploaded_at=document_data["uploaded_at"]
    )


@router.get("/", response_model=List[DocumentResponse])
def get_documents(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all documents for the current doctor.
    """
    import json
    
    # Get user from current session
    db_user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not db_user or not db_user.attached_document:
        return []
    
    try:
        document_data = json.loads(db_user.attached_document)
        # If it's a single document, convert to list
        if isinstance(document_data, dict):
            document_data = [document_data]
        
        # Convert to DocumentResponse
        documents = []
        for doc in document_data:
            file_path_str = doc.get("file_path", "")
            file_id = doc.get("id", file_path_str.split("/")[-1].split(".")[0] if file_path_str else "")
            documents.append(DocumentResponse(
                id=file_id,
                type=doc.get("type", ""),
                file_name=doc.get("file_name", ""),
                file_url=doc.get("file_url", ""),
                status=doc.get("status", "pending"),
                uploaded_at=doc.get("uploaded_at", ""),
                reviewed_at=doc.get("reviewed_at")
            ))
        return documents
    except (json.JSONDecodeError, TypeError):
        return []


@router.get("/{file_name}")
async def get_document_file(
    file_name: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download/view a document file.
    """
    # Verify file belongs to current user first
    import json
    db_user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not db_user or not db_user.attached_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        doc_data = json.loads(db_user.attached_document)
        if isinstance(doc_data, dict):
            doc_data = [doc_data]
        
        # Find the document that matches the file_name
        matching_doc = None
        for doc in doc_data:
            # Get the stored file name from file_path or file_url
            stored_file_path = doc.get("file_path", "")
            stored_file_url = doc.get("file_url", "")
            
            # Extract file name from path (handle both / and \ separators)
            stored_file_name = None
            if stored_file_path:
                # Handle Windows and Unix paths
                stored_file_name = stored_file_path.replace("\\", "/").split("/")[-1]
            elif stored_file_url:
                stored_file_name = stored_file_url.split("/")[-1]
            
            # Match by exact filename
            if stored_file_name and file_name == stored_file_name:
                matching_doc = doc
                break
        
        if not matching_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get the actual file path
        stored_file_path = matching_doc.get("file_path", "")
        if stored_file_path:
            # Use the stored path, but normalize it
            file_path = Path(stored_file_path)
        else:
            # Fallback: construct path from file_name
            file_path = UPLOAD_DIR / file_name
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk"
            )
        
        # Determine media type based on file extension
        media_type = "application/octet-stream"
        file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        if file_ext == 'pdf':
            media_type = "application/pdf"
        elif file_ext in ['jpg', 'jpeg']:
            media_type = "image/jpeg"
        elif file_ext == 'png':
            media_type = "image/png"
        
        return FileResponse(
            path=str(file_path),
            filename=matching_doc.get("file_name", file_name),
            media_type=media_type
        )
    except (json.JSONDecodeError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.delete("/{file_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    file_name: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document.
    """
    import json
    
    # Get user from current session
    db_user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not db_user or not db_user.attached_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        doc_data = json.loads(db_user.attached_document)
        if isinstance(doc_data, dict):
            doc_data = [doc_data]
        
        # Find and remove the document
        updated_docs = [doc for doc in doc_data if file_name not in doc.get("file_path", "")]
        
        if len(updated_docs) == len(doc_data):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Delete file from filesystem
        file_path = UPLOAD_DIR / file_name
        if file_path.exists():
            file_path.unlink()
        
        # Update user's attached_document
        if updated_docs:
            db_user.attached_document = json.dumps(updated_docs[0] if len(updated_docs) == 1 else updated_docs)
        else:
            db_user.attached_document = None
        
        db.commit()
    except (json.JSONDecodeError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )

