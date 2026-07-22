"""
SQLAlchemy database models
"""
from datetime import datetime
from uuid import uuid4, UUID as PyUUID
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, Text, ForeignKey, Numeric, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# For SQLite compatibility, use String for UUID and JSON for JSONB
# VECTOR support is removed for SQLite compatibility

Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default="project_manager")
    organization = Column(String(255))
    phone = Column(String(50))
    avatar_url = Column(Text)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owned_projects = relationship("Project", back_populates="owner")
    activity_progress = relationship("ActivityProgress", back_populates="reported_by_user")
    risks_owned = relationship("Risk", back_populates="owner")
    conversations = relationship("Conversation", back_populates="user")


class Project(Base):
    """Project model"""
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    client_name = Column(String(255))
    location = Column(String(255))
    project_type = Column(String(100))
    contract_value = Column(Numeric(20, 2))
    currency = Column(String(10), default="USD")
    start_date = Column(Date, nullable=False)
    planned_end_date = Column(Date, nullable=False)
    actual_end_date = Column(Date)
    status = Column(String(50), default="planning", index=True)
    progress_percentage = Column(Numeric(5, 2), default=0)
    budget_consumed = Column(Numeric(20, 2), default=0)
    total_budget = Column(Numeric(20, 2))
    owner_id = Column(String(36), ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="owned_projects")
    schedules = relationship("Schedule", back_populates="project", cascade="all, delete-orphan")
    purchase_orders = relationship("PurchaseOrder", back_populates="project", cascade="all, delete-orphan")
    inventory = relationship("Inventory", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="project", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="project", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="project", cascade="all, delete-orphan")
    health_metrics = relationship("ProjectHealth", back_populates="project", cascade="all, delete-orphan")
    supplier_performance = relationship("SupplierPerformance", back_populates="project")
    conversations = relationship("Conversation", back_populates="project")
    agent_memory = relationship("AgentMemory", back_populates="project")
    agent_logs = relationship("AgentLog", back_populates="project")
    notifications = relationship("Notification", back_populates="project")


class Schedule(Base):
    """Schedule model"""
    __tablename__ = "schedules"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    source_type = Column(String(50))
    source_file_path = Column(Text)
    baseline_date = Column(Date, nullable=False)
    data_date = Column(Date)
    total_activities = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="schedules")
    activities = relationship("Activity", back_populates="schedule", cascade="all, delete-orphan")
    dependencies = relationship("Dependency", back_populates="schedule", cascade="all, delete-orphan")
    critical_path = relationship("CriticalPath", back_populates="schedule", cascade="all, delete-orphan")


class Activity(Base):
    """Activity model"""
    __tablename__ = "activities"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    schedule_id = Column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(String(100), nullable=False)
    activity_name = Column(String(500), nullable=False)
    activity_type = Column(String(100))
    wbs_code = Column(String(100), index=True)
    original_duration = Column(Integer)
    remaining_duration = Column(Integer)
    actual_duration = Column(Integer)
    percent_complete = Column(Numeric(5, 2), default=0)
    early_start = Column(Date)
    early_finish = Column(Date)
    late_start = Column(Date)
    late_finish = Column(Date)
    actual_start = Column(Date)
    actual_finish = Column(Date)
    start_date = Column(Date)
    finish_date = Column(Date)
    is_critical = Column(Boolean, default=False, index=True)
    is_milestone = Column(Boolean, default=False)
    calendar_id = Column(String(100))
    cost_code = Column(String(100))
    resource_ids = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    schedule = relationship("Schedule", back_populates="activities")
    progress_records = relationship("ActivityProgress", back_populates="activity", cascade="all, delete-orphan")
    predecessor_dependencies = relationship("Dependency", foreign_keys="Dependency.predecessor_id", back_populates="predecessor")
    successor_dependencies = relationship("Dependency", foreign_keys="Dependency.successor_id", back_populates="successor")
    critical_path_records = relationship("CriticalPath", back_populates="activity")


class Dependency(Base):
    """Dependency model"""
    __tablename__ = "dependencies"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    schedule_id = Column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    predecessor_id = Column(String(36), ForeignKey("activities.id"), nullable=False, index=True)
    successor_id = Column(String(36), ForeignKey("activities.id"), nullable=False, index=True)
    dependency_type = Column(String(50), default="finish_to_start")
    lag = Column(Integer, default=0)
    is_critical = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    schedule = relationship("Schedule", back_populates="dependencies")
    predecessor = relationship("Activity", foreign_keys=[predecessor_id], back_populates="predecessor_dependencies")
    successor = relationship("Activity", foreign_keys=[successor_id], back_populates="successor_dependencies")


class Supplier(Base):
    """Supplier model"""
    __tablename__ = "suppliers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    supplier_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), index=True)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    country = Column(String(100))
    city = Column(String(100))
    rating = Column(Numeric(3, 2), default=0, index=True)
    total_orders = Column(Integer, default=0)
    on_time_delivery_rate = Column(Numeric(5, 2), default=0)
    quality_score = Column(Numeric(5, 2), default=0)
    is_active = Column(Boolean, default=True)
    is_preferred = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    performance_records = relationship("SupplierPerformance", back_populates="supplier", cascade="all, delete-orphan")


class Material(Base):
    """Material model"""
    __tablename__ = "materials"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    material_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    unit = Column(String(50))
    unit_cost = Column(Numeric(10, 2))
    lead_time = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="material")
    inventory_records = relationship("Inventory", back_populates="material")


class PurchaseOrder(Base):
    """Purchase Order model"""
    __tablename__ = "purchase_orders"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    po_number = Column(String(100), unique=True, nullable=False, index=True)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False, index=True)
    issue_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date)
    actual_delivery_date = Column(Date)
    status = Column(String(50), default="pending", index=True)
    total_amount = Column(Numeric(20, 2))
    currency = Column(String(10), default="USD")
    priority = Column(String(50), default="normal")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="purchase_orders")
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    """Purchase Order Item model"""
    __tablename__ = "purchase_order_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    purchase_order_id = Column(String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    material_id = Column(String(36), ForeignKey("materials.id"), index=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(15, 2), nullable=False)
    unit = Column(String(50))
    unit_price = Column(Numeric(10, 2))
    total_price = Column(Numeric(20, 2))
    quantity_received = Column(Numeric(15, 2), default=0)
    quantity_pending = Column(Numeric(15, 2))
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    material = relationship("Material", back_populates="purchase_order_items")


class Inventory(Base):
    """Inventory model"""
    __tablename__ = "inventory"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    material_id = Column(String(36), ForeignKey("materials.id"), index=True)
    warehouse_location = Column(String(255))
    quantity_on_hand = Column(Numeric(15, 2), default=0)
    quantity_reserved = Column(Numeric(15, 2), default=0)
    quantity_available = Column(Numeric(15, 2), default=0)
    minimum_stock_level = Column(Numeric(15, 2))
    maximum_stock_level = Column(Numeric(15, 2))
    reorder_point = Column(Numeric(15, 2))
    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="inventory")
    material = relationship("Material", back_populates="inventory_records")


class Risk(Base):
    """Risk model"""
    __tablename__ = "risks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    risk_source = Column(String(100))
    probability = Column(Numeric(5, 2))
    impact = Column(Numeric(5, 2))
    risk_score = Column(Numeric(5, 2), index=True)
    severity = Column(String(50), index=True)
    confidence = Column(Numeric(5, 2))
    status = Column(String(50), default="open", index=True)
    identified_date = Column(Date, default=datetime.utcnow().date())
    target_closure_date = Column(Date)
    actual_closure_date = Column(Date)
    owner_id = Column(String(36), ForeignKey("users.id"))
    related_activities = Column(JSON)
    related_suppliers = Column(JSON)
    explanation = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="risks")
    owner = relationship("User", back_populates="risks_owned")


class Recommendation(Base):
    """Recommendation model"""
    __tablename__ = "recommendations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    recommendation_type = Column(String(100), index=True)
    expected_impact = Column(JSON)
    confidence = Column(Numeric(5, 2))
    estimated_days_saved = Column(Integer)
    estimated_cost_impact = Column(Numeric(20, 2))
    priority = Column(String(50), default="medium", index=True)
    status = Column(String(50), default="pending", index=True)
    related_risks = Column(JSON)
    related_activities = Column(JSON)
    related_suppliers = Column(JSON)
    explanation = Column(Text)
    created_by_agent = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="recommendations")


class Prediction(Base):
    """Prediction model"""
    __tablename__ = "predictions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_type = Column(String(100), nullable=False, index=True)
    prediction_date = Column(Date, nullable=False)
    target_date = Column(Date)
    predicted_value = Column(Numeric(20, 2))
    actual_value = Column(Numeric(20, 2))
    confidence = Column(Numeric(5, 2))
    model_version = Column(String(50))
    features = Column(JSON)
    explanation = Column(Text)
    is_accurate = Column(Boolean)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="predictions")


class Report(Base):
    """Report model"""
    __tablename__ = "reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = Column(String(100), nullable=False, index=True)
    report_name = Column(String(255), nullable=False)
    report_date = Column(Date, nullable=False, index=True)
    period_start = Column(Date)
    period_end = Column(Date)
    generated_by_agent = Column(String(100))
    content = Column(JSON)
    summary = Column(Text)
    key_insights = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="reports")


class ProjectHealth(Base):
    """Project Health model"""
    __tablename__ = "project_health"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_date = Column(Date, nullable=False, index=True)
    overall_health_score = Column(Numeric(5, 2))
    schedule_health_score = Column(Numeric(5, 2))
    procurement_health_score = Column(Numeric(5, 2))
    supplier_health_score = Column(Numeric(5, 2))
    risk_score = Column(Numeric(5, 2))
    cost_performance_index = Column(Numeric(5, 2))
    schedule_performance_index = Column(Numeric(5, 2))
    completion_percentage = Column(Numeric(5, 2))
    on_time_activities_percentage = Column(Numeric(5, 2))
    on_budget_percentage = Column(Numeric(5, 2))
    open_risks_count = Column(Integer)
    critical_risks_count = Column(Integer)
    open_recommendations_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="health_metrics")


class ActivityProgress(Base):
    """Activity Progress model"""
    __tablename__ = "activity_progress"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    activity_id = Column(String(36), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)
    progress_percentage = Column(Numeric(5, 2))
    status = Column(String(50))
    notes = Column(Text)
    reported_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    activity = relationship("Activity", back_populates="progress_records")
    reported_by_user = relationship("User", back_populates="activity_progress")


class SupplierPerformance(Base):
    """Supplier Performance model"""
    __tablename__ = "supplier_performance"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), index=True)
    evaluation_date = Column(Date, nullable=False, index=True)
    on_time_delivery_rate = Column(Numeric(5, 2))
    quality_rating = Column(Numeric(5, 2))
    responsiveness_rating = Column(Numeric(5, 2))
    price_competitiveness = Column(Numeric(5, 2))
    overall_score = Column(Numeric(5, 2))
    total_deliveries = Column(Integer)
    on_time_deliveries = Column(Integer)
    late_deliveries = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="performance_records")
    project = relationship("Project", back_populates="supplier_performance")


class CriticalPath(Base):
    """Critical Path model"""
    __tablename__ = "critical_path"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    schedule_id = Column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    calculation_date = Column(Date, nullable=False, index=True)
    activity_id = Column(String(36), ForeignKey("activities.id"), nullable=False, index=True)
    sequence_order = Column(Integer)
    total_float = Column(Integer)
    free_float = Column(Integer)
    is_bottleneck = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    schedule = relationship("Schedule", back_populates="critical_path")
    activity = relationship("Activity", back_populates="critical_path_records")


class AgentMemory(Base):
    """Agent Memory model"""
    __tablename__ = "agent_memory"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_name = Column(String(100), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    memory_type = Column(String(100), index=True)
    memory_key = Column(String(255))
    memory_value = Column(Text)
    embedding = Column(Text)  # Stored as JSON string for SQLite
    confidence = Column(Numeric(5, 2))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="agent_memory")


class AgentLog(Base):
    """Agent Log model"""
    __tablename__ = "agent_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_name = Column(String(100), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    execution_type = Column(String(100), index=True)
    input_data = Column(Text)
    output_data = Column(Text)
    execution_time_ms = Column(Integer)
    status = Column(String(50))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Relationships
    project = relationship("Project", back_populates="agent_logs")


class Conversation(Base):
    """Conversation model"""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), index=True)
    session_id = Column(String(36), nullable=False, index=True)
    message = Column(Text, nullable=False)
    role = Column(String(50), nullable=False)
    context = Column(JSON)
    citations = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    project = relationship("Project", back_populates="conversations")


class SystemLog(Base):
    """System Log model"""
    __tablename__ = "system_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    level = Column(String(20), nullable=False, index=True)
    component = Column(String(100), index=True)
    message = Column(Text, nullable=False)
    details = Column(Text)
    user_id = Column(String(36), ForeignKey("users.id"))
    ip_address = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class Notification(Base):
    """Smart Notification model - alerts generated from project risk conditions"""
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(String(50), nullable=False, index=True)  # schedule_delay, procurement_issue, risk_alert, pending_approval, compliance_failure
    severity = Column(String(20), nullable=False, index=True)  # critical, high, medium, low
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    source = Column(String(100))  # which agent/rule generated it
    related_entity_type = Column(String(50))  # risk, purchase_order, recommendation, schedule
    related_entity_id = Column(String(36), index=True)
    channels = Column(JSON)  # e.g. ["dashboard", "email"]
    is_read = Column(Boolean, default=False, index=True)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    project = relationship("Project", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_dedup", "project_id", "notification_type", "related_entity_id"),
    )
