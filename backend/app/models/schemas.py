"""
Pydantic schemas for API request/response validation
"""
from datetime import datetime, date
from uuid import UUID
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================
# User Schemas
# ============================================

class UserBase(BaseModel):
    email: str
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = "project_manager"
    organization: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============================================
# Project Schemas
# ============================================

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    client_name: Optional[str] = None
    location: Optional[str] = None
    project_type: Optional[str] = None
    contract_value: Optional[float] = None
    currency: str = "USD"
    start_date: date
    planned_end_date: date
    total_budget: Optional[float] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    progress_percentage: Optional[float] = None
    budget_consumed: Optional[float] = None
    actual_end_date: Optional[date] = None


class ProjectResponse(ProjectBase):
    id: UUID
    status: str
    progress_percentage: float
    budget_consumed: float
    actual_end_date: Optional[date]
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    id: UUID
    name: str
    code: str
    status: str
    progress_percentage: float
    location: Optional[str] = None
    start_date: date
    planned_end_date: date
    overall_health_score: Optional[float]
    schedule_health_score: Optional[float]
    procurement_health_score: Optional[float]
    risk_score: Optional[float]
    open_risks_count: Optional[int]
    critical_risks_count: Optional[int]
    total_schedules: int
    total_purchase_orders: int


# ============================================
# Schedule Schemas
# ============================================

class ScheduleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., min_length=1, max_length=50)
    source_type: Optional[str] = None
    baseline_date: date


class ScheduleCreate(ScheduleBase):
    project_id: UUID


class ScheduleResponse(ScheduleBase):
    id: UUID
    project_id: UUID
    source_file_path: Optional[str]
    data_date: Optional[date]
    total_activities: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Activity Schemas
# ============================================

class ActivityBase(BaseModel):
    activity_id: str
    activity_name: str
    activity_type: Optional[str] = None
    wbs_code: Optional[str] = None
    original_duration: Optional[int] = None
    remaining_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    percent_complete: float = 0
    early_start: Optional[date] = None
    early_finish: Optional[date] = None
    late_start: Optional[date] = None
    late_finish: Optional[date] = None
    actual_start: Optional[date] = None
    actual_finish: Optional[date] = None
    start_date: Optional[date] = None
    finish_date: Optional[date] = None
    is_critical: bool = False
    is_milestone: bool = False


class ActivityCreate(ActivityBase):
    schedule_id: UUID


class ActivityResponse(ActivityBase):
    id: UUID
    schedule_id: UUID
    calendar_id: Optional[str]
    cost_code: Optional[str]
    resource_ids: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Supplier Schemas
# ============================================

class SupplierBase(BaseModel):
    supplier_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = None
    is_active: Optional[bool] = None
    is_preferred: Optional[bool] = None


class SupplierResponse(SupplierBase):
    id: UUID
    rating: float
    total_orders: int
    on_time_delivery_rate: float
    quality_score: float
    is_active: bool
    is_preferred: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Purchase Order Schemas
# ============================================

class PurchaseOrderBase(BaseModel):
    po_number: str = Field(..., min_length=1, max_length=100)
    supplier_id: UUID
    issue_date: date
    expected_delivery_date: Optional[date] = None
    total_amount: Optional[float] = None
    currency: str = "USD"
    priority: str = "normal"


class PurchaseOrderCreate(PurchaseOrderBase):
    project_id: UUID


class PurchaseOrderUpdate(BaseModel):
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    status: Optional[str] = None
    total_amount: Optional[float] = None
    priority: Optional[str] = None


class PurchaseOrderResponse(PurchaseOrderBase):
    id: UUID
    project_id: UUID
    actual_delivery_date: Optional[date]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Risk Schemas
# ============================================

class RiskBase(BaseModel):
    risk_code: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str
    risk_source: Optional[str] = None
    probability: float = Field(..., ge=0, le=100)
    impact: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=100)
    target_closure_date: Optional[date] = None


class RiskCreate(RiskBase):
    project_id: UUID
    owner_id: Optional[UUID] = None


class RiskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    probability: Optional[float] = None
    impact: Optional[float] = None
    confidence: Optional[float] = None
    status: Optional[str] = None
    target_closure_date: Optional[date] = None
    actual_closure_date: Optional[date] = None


class RiskResponse(RiskBase):
    id: UUID
    project_id: UUID
    risk_score: float
    severity: str
    status: str
    identified_date: date
    owner_id: Optional[UUID]
    related_activities: Optional[List[str]]
    related_suppliers: Optional[List[str]]
    explanation: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Recommendation Schemas
# ============================================

class RecommendationBase(BaseModel):
    recommendation_code: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: str
    recommendation_type: str
    confidence: float = Field(..., ge=0, le=100)
    estimated_days_saved: Optional[int] = None
    estimated_cost_impact: Optional[float] = None
    priority: str = "medium"


class RecommendationCreate(RecommendationBase):
    project_id: UUID


class RecommendationUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None


class RecommendationResponse(RecommendationBase):
    id: UUID
    project_id: UUID
    expected_impact: Optional[Dict[str, Any]]
    status: str
    related_risks: Optional[List[str]]
    related_activities: Optional[List[str]]
    related_suppliers: Optional[List[str]]
    explanation: Optional[str]
    created_by_agent: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Prediction Schemas
# ============================================

class PredictionBase(BaseModel):
    prediction_type: str
    prediction_date: date
    target_date: Optional[date] = None
    predicted_value: Optional[float] = None
    confidence: Optional[float] = None
    model_version: Optional[str] = None


class PredictionCreate(PredictionBase):
    project_id: UUID


class PredictionResponse(PredictionBase):
    id: UUID
    project_id: UUID
    actual_value: Optional[float]
    features: Optional[Dict[str, Any]]
    explanation: Optional[str]
    is_accurate: Optional[bool]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Report Schemas
# ============================================

class ReportBase(BaseModel):
    report_type: str
    report_name: str
    report_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class ReportCreate(ReportBase):
    project_id: UUID


class ReportResponse(ReportBase):
    id: UUID
    project_id: UUID
    generated_by_agent: Optional[str]
    content: Optional[Dict[str, Any]]
    summary: Optional[str]
    key_insights: Optional[List[str]]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Project Health Schemas
# ============================================

class ProjectHealthBase(BaseModel):
    metric_date: date
    overall_health_score: Optional[float] = None
    schedule_health_score: Optional[float] = None
    procurement_health_score: Optional[float] = None
    supplier_health_score: Optional[float] = None
    risk_score: Optional[float] = None
    cost_performance_index: Optional[float] = None
    schedule_performance_index: Optional[float] = None
    completion_percentage: Optional[float] = None
    on_time_activities_percentage: Optional[float] = None
    on_budget_percentage: Optional[float] = None
    open_risks_count: Optional[int] = None
    critical_risks_count: Optional[int] = None
    open_recommendations_count: Optional[int] = None


class ProjectHealthCreate(ProjectHealthBase):
    project_id: UUID


class ProjectHealthResponse(ProjectHealthBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Conversation Schemas
# ============================================

class ConversationCreate(BaseModel):
    message: str
    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None


class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: Optional[UUID]
    session_id: UUID
    message: str
    role: str
    context: Optional[Dict[str, Any]]
    citations: Optional[List[str]]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Agent Execution Schemas
# ============================================

class AgentExecutionRequest(BaseModel):
    agent_name: str
    project_id: UUID
    execution_type: str
    input_data: Optional[Dict[str, Any]] = None


class AgentExecutionResponse(BaseModel):
    execution_id: UUID
    agent_name: str
    project_id: UUID
    execution_type: str
    status: str
    output_data: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime


# ============================================
# File Upload Schemas
# ============================================

class FileUploadResponse(BaseModel):
    filename: str
    file_path: str
    file_size: int
    upload_type: str
    project_id: Optional[UUID] = None
    parsed_data: Optional[Dict[str, Any]] = None


# ============================================
# Analytics Schemas
# ============================================

class DashboardMetrics(BaseModel):
    project_health: float
    schedule_health: float
    procurement_health: float
    risk_score: float
    supplier_health: float
    completion_percentage: float
    open_risks: int
    critical_risks: int
    active_recommendations: int


class TrendData(BaseModel):
    date: date
    value: float
    label: Optional[str] = None


class ChartData(BaseModel):
    title: str
    data: List[Dict[str, Any]]
    type: str  # line, bar, pie, etc.


class HeatmapData(BaseModel):
    x: str
    y: str
    value: float
    label: Optional[str] = None


# ============================================
# Notification Schemas
# ============================================

class NotificationResponse(BaseModel):
    id: UUID
    project_id: UUID
    notification_type: str
    severity: str
    title: str
    message: str
    source: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    channels: Optional[List[str]] = None
    is_read: bool
    email_sent: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCountResponse(BaseModel):
    unread: int
    critical: int


# ============================================
# Inventory Status Schemas
# ============================================

class InventoryStatusResponse(BaseModel):
    """Material stock position with reorder guidance for site engineers."""
    inventory_id: UUID
    material_code: str
    material_name: str
    category: Optional[str] = None
    unit: Optional[str] = None
    unit_cost: Optional[float] = None
    lead_time_days: Optional[int] = None
    warehouse_location: Optional[str] = None
    quantity_on_hand: float
    quantity_reserved: float
    quantity_available: float
    minimum_stock_level: Optional[float] = None
    reorder_point: Optional[float] = None
    reorder_quantity: float  # how much to order now (0 = stock OK)
    stock_status: str  # ok | reorder | critical
