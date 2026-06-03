from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, func

from app.core.database import Base


class Document(Base):
    """A plain-text business record indexed for RAG retrieval.

    The embedding itself lives in the vector store (ChromaDB), keyed back to this
    row by source_type + source_id, so the relational schema stays unchanged.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    source_type = Column(String(100))     # invoice, order, product, report
    source_id = Column(Integer)           # id of the underlying record
    content = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
