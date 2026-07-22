-- AI Project Monitoring & Risk Engine - Database Schema
-- Enterprise-grade PostgreSQL schema for multi-agent AI system

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'project_manager', -- admin, project_manager, stakeholder, viewer
    organization VARCHAR(255),
    phone VARCHAR(50),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization ON users(organization);

-- ============================================
-- PROJECTS
-- ============================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    client_name VARCHAR(255),
    location VARCHAR(255),
    project_type VARCHAR(100), -- epc, construction, infrastructure
    contract_value DECIMAL(20, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    start_date DATE NOT NULL,
    planned_end_date DATE NOT NULL,
    actual_end_date DATE,
    status VARCHAR(50) DEFAULT 'planning', -- planning, active, on_hold, completed, cancelled
    progress_percentage DECIMAL(5, 2) DEFAULT 0,
    budget_consumed DECIMAL(20, 2) DEFAULT 0,
    total_budget DECIMAL(20, 2),
    owner_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_projects_code ON projects(code);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_owner ON projects(owner_id);

-- ============================================
-- SCHEDULES
-- ============================================

CREATE TABLE schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    source_type VARCHAR(50), -- primavera, ms_project, excel, csv
    source_file_path TEXT,
    baseline_date DATE NOT NULL,
    data_date DATE,
    total_activities INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, version)
);

CREATE INDEX idx_schedules_project ON schedules(project_id);
CREATE INDEX idx_schedules_version ON schedules(project_id, version);

-- ============================================
-- ACTIVITIES
-- ============================================

CREATE TABLE activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id UUID NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    activity_id VARCHAR(100) NOT NULL,
    activity_name VARCHAR(500) NOT NULL,
    activity_type VARCHAR(100), -- task, milestone, summary, wbs
    wbs_code VARCHAR(100),
    original_duration INTEGER, -- in days
    remaining_duration INTEGER,
    actual_duration INTEGER,
    percent_complete DECIMAL(5, 2) DEFAULT 0,
    early_start DATE,
    early_finish DATE,
    late_start DATE,
    late_finish DATE,
    actual_start DATE,
    actual_finish DATE,
    start_date DATE,
    finish_date DATE,
    is_critical BOOLEAN DEFAULT false,
    is_milestone BOOLEAN DEFAULT false,
    calendar_id VARCHAR(100),
    cost_code VARCHAR(100),
    resource_ids TEXT, -- JSON array of resource IDs
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activities_schedule ON activities(schedule_id);
CREATE INDEX idx_activities_activity_id ON activities(activity_id);
CREATE INDEX idx_activities_wbs ON activities(wbs_code);
CREATE INDEX idx_activities_critical ON activities(is_critical) WHERE is_critical = true;

-- ============================================
-- DEPENDENCIES
-- ============================================

CREATE TABLE dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id UUID NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    predecessor_id UUID NOT NULL REFERENCES activities(id),
    successor_id UUID NOT NULL REFERENCES activities(id),
    dependency_type VARCHAR(50) DEFAULT 'finish_to_start', -- finish_to_start, start_to_start, finish_to_finish, start_to_finish
    lag INTEGER DEFAULT 0,
    is_critical BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dependencies_schedule ON dependencies(schedule_id);
CREATE INDEX idx_dependencies_predecessor ON dependencies(predecessor_id);
CREATE INDEX idx_dependencies_successor ON dependencies(successor_id);

-- ============================================
-- SUPPLIERS
-- ============================================

CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplier_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100), -- material, equipment, service
    contact_person VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    country VARCHAR(100),
    city VARCHAR(100),
    rating DECIMAL(3, 2) DEFAULT 0, -- 0-5
    total_orders INTEGER DEFAULT 0,
    on_time_delivery_rate DECIMAL(5, 2) DEFAULT 0,
    quality_score DECIMAL(5, 2) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    is_preferred BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_suppliers_code ON suppliers(supplier_code);
CREATE INDEX idx_suppliers_category ON suppliers(category);
CREATE INDEX idx_suppliers_rating ON suppliers(rating);

-- ============================================
-- MATERIALS
-- ============================================

CREATE TABLE materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    material_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    unit VARCHAR(50), -- kg, m, pcs, etc
    unit_cost DECIMAL(10, 2),
    lead_time INTEGER, -- in days
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_materials_code ON materials(material_code);
CREATE INDEX idx_materials_category ON materials(category);

-- ============================================
-- PURCHASE ORDERS
-- ============================================

CREATE TABLE purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    po_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id UUID NOT NULL REFERENCES suppliers(id),
    issue_date DATE NOT NULL,
    expected_delivery_date DATE,
    actual_delivery_date DATE,
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, ordered, shipped, delivered, cancelled
    total_amount DECIMAL(20, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    priority VARCHAR(50) DEFAULT 'normal', -- low, normal, high, urgent
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_purchase_orders_project ON purchase_orders(project_id);
CREATE INDEX idx_purchase_orders_supplier ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);
CREATE INDEX idx_purchase_orders_po_number ON purchase_orders(po_number);

-- ============================================
-- PURCHASE ORDER ITEMS
-- ============================================

CREATE TABLE purchase_order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    material_id UUID REFERENCES materials(id),
    description VARCHAR(500) NOT NULL,
    quantity DECIMAL(15, 2) NOT NULL,
    unit VARCHAR(50),
    unit_price DECIMAL(10, 2),
    total_price DECIMAL(20, 2),
    quantity_received DECIMAL(15, 2) DEFAULT 0,
    quantity_pending DECIMAL(15, 2),
    status VARCHAR(50) DEFAULT 'pending', -- pending, ordered, partial, complete
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_po_items_po ON purchase_order_items(purchase_order_id);
CREATE INDEX idx_po_items_material ON purchase_order_items(material_id);

-- ============================================
-- INVENTORY
-- ============================================

CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    material_id UUID REFERENCES materials(id),
    warehouse_location VARCHAR(255),
    quantity_on_hand DECIMAL(15, 2) DEFAULT 0,
    quantity_reserved DECIMAL(15, 2) DEFAULT 0,
    quantity_available DECIMAL(15, 2) DEFAULT 0,
    minimum_stock_level DECIMAL(15, 2),
    maximum_stock_level DECIMAL(15, 2),
    reorder_point DECIMAL(15, 2),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inventory_project ON inventory(project_id);
CREATE INDEX idx_inventory_material ON inventory(material_id);

-- ============================================
-- RISKS
-- ============================================

CREATE TABLE risks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    risk_code VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100), -- schedule, procurement, resource, financial, technical, external
    risk_source VARCHAR(100), -- supplier, activity, resource, weather, etc
    probability DECIMAL(5, 2), -- 0-100
    impact DECIMAL(5, 2), -- 0-100
    risk_score DECIMAL(5, 2), -- probability * impact
    severity VARCHAR(50), -- low, medium, high, critical
    confidence DECIMAL(5, 2), -- 0-100
    status VARCHAR(50) DEFAULT 'open', -- open, mitigating, closed, accepted
    identified_date DATE DEFAULT CURRENT_DATE,
    target_closure_date DATE,
    actual_closure_date DATE,
    owner_id UUID REFERENCES users(id),
    related_activities TEXT, -- JSON array of activity IDs
    related_suppliers TEXT, -- JSON array of supplier IDs
    explanation TEXT, -- AI-generated explanation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_risks_project ON risks(project_id);
CREATE INDEX idx_risks_category ON risks(category);
CREATE INDEX idx_risks_status ON risks(status);
CREATE INDEX idx_risks_score ON risks(risk_score);
CREATE INDEX idx_risks_severity ON risks(severity);

-- ============================================
-- RECOMMENDATIONS
-- ============================================

CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    recommendation_code VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    recommendation_type VARCHAR(100), -- supplier_change, resource_increase, reschedule, parallel_execution, extra_shift, inventory_transfer
    expected_impact TEXT, -- JSON with impact details
    confidence DECIMAL(5, 2), -- 0-100
    estimated_days_saved INTEGER,
    estimated_cost_impact DECIMAL(20, 2),
    priority VARCHAR(50) DEFAULT 'medium', -- low, medium, high, urgent
    status VARCHAR(50) DEFAULT 'pending', -- pending, accepted, rejected, implemented
    related_risks TEXT, -- JSON array of risk IDs
    related_activities TEXT, -- JSON array of activity IDs
    related_suppliers TEXT, -- JSON array of supplier IDs
    explanation TEXT, -- AI-generated explanation
    created_by_agent VARCHAR(100), -- recommendation_agent
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recommendations_project ON recommendations(project_id);
CREATE INDEX idx_recommendations_type ON recommendations(recommendation_type);
CREATE INDEX idx_recommendations_status ON recommendations(status);
CREATE INDEX idx_recommendations_priority ON recommendations(priority);

-- ============================================
-- PREDICTIONS
-- ============================================

CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    prediction_type VARCHAR(100) NOT NULL, -- delay, cost_overrun, supplier_delay, material_shortage
    prediction_date DATE NOT NULL,
    target_date DATE,
    predicted_value DECIMAL(20, 2),
    actual_value DECIMAL(20, 2),
    confidence DECIMAL(5, 2),
    model_version VARCHAR(50),
    features TEXT, -- JSON with features used
    explanation TEXT, -- AI-generated explanation
    is_accurate BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_predictions_project ON predictions(project_id);
CREATE INDEX idx_predictions_type ON predictions(prediction_type);
CREATE INDEX idx_predictions_date ON predictions(prediction_date);

-- ============================================
-- REPORTS
-- ============================================

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    report_type VARCHAR(100) NOT NULL, -- daily, weekly, monthly, executive, risk, schedule, procurement
    report_name VARCHAR(255) NOT NULL,
    report_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,
    generated_by_agent VARCHAR(100), -- executive_summary_agent
    content TEXT, -- JSON with report content
    summary TEXT,
    key_insights TEXT, -- JSON array
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reports_project ON reports(project_id);
CREATE INDEX idx_reports_type ON reports(report_type);
CREATE INDEX idx_reports_date ON reports(report_date);

-- ============================================
-- PROJECT HEALTH METRICS
-- ============================================

CREATE TABLE project_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    overall_health_score DECIMAL(5, 2), -- 0-100
    schedule_health_score DECIMAL(5, 2), -- 0-100
    procurement_health_score DECIMAL(5, 2), -- 0-100
    supplier_health_score DECIMAL(5, 2), -- 0-100
    risk_score DECIMAL(5, 2), -- 0-100
    cost_performance_index DECIMAL(5, 2),
    schedule_performance_index DECIMAL(5, 2),
    completion_percentage DECIMAL(5, 2),
    on_time_activities_percentage DECIMAL(5, 2),
    on_budget_percentage DECIMAL(5, 2),
    open_risks_count INTEGER,
    critical_risks_count INTEGER,
    open_recommendations_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, metric_date)
);

CREATE INDEX idx_project_health_project ON project_health(project_id);
CREATE INDEX idx_project_health_date ON project_health(metric_date);

-- ============================================
-- ACTIVITY PROGRESS
-- ============================================

CREATE TABLE activity_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    report_date DATE NOT NULL,
    progress_percentage DECIMAL(5, 2),
    status VARCHAR(50),
    notes TEXT,
    reported_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(activity_id, report_date)
);

CREATE INDEX idx_activity_progress_activity ON activity_progress(activity_id);
CREATE INDEX idx_activity_progress_date ON activity_progress(report_date);

-- ============================================
-- SUPPLIER PERFORMANCE
-- ============================================

CREATE TABLE supplier_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id),
    evaluation_date DATE NOT NULL,
    on_time_delivery_rate DECIMAL(5, 2),
    quality_rating DECIMAL(5, 2),
    responsiveness_rating DECIMAL(5, 2),
    price_competitiveness DECIMAL(5, 2),
    overall_score DECIMAL(5, 2),
    total_deliveries INTEGER,
    on_time_deliveries INTEGER,
    late_deliveries INTEGER,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(supplier_id, project_id, evaluation_date)
);

CREATE INDEX idx_supplier_performance_supplier ON supplier_performance(supplier_id);
CREATE INDEX idx_supplier_performance_project ON supplier_performance(project_id);
CREATE INDEX idx_supplier_performance_date ON supplier_performance(evaluation_date);

-- ============================================
-- CRITICAL PATH
-- ============================================

CREATE TABLE critical_path (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id UUID NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    calculation_date DATE NOT NULL,
    activity_id UUID NOT NULL REFERENCES activities(id),
    sequence_order INTEGER,
    total_float INTEGER,
    free_float INTEGER,
    is_bottleneck BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_critical_path_schedule ON critical_path(schedule_id);
CREATE INDEX idx_critical_path_date ON critical_path(calculation_date);
CREATE INDEX idx_critical_path_activity ON critical_path(activity_id);

-- ============================================
-- AGENT MEMORY
-- ============================================

CREATE TABLE agent_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    memory_type VARCHAR(100), -- delay_history, supplier_history, lesson_learned, pattern
    memory_key VARCHAR(255),
    memory_value TEXT,
    embedding vector(1536),
    confidence DECIMAL(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_memory_agent ON agent_memory(agent_name);
CREATE INDEX idx_agent_memory_project ON agent_memory(project_id);
CREATE INDEX idx_agent_memory_type ON agent_memory(memory_type);
CREATE INDEX idx_agent_memory_embedding ON agent_memory USING ivfflat (embedding vector_cosine_ops);

-- ============================================
-- AGENT EXECUTION LOGS
-- ============================================

CREATE TABLE agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    execution_type VARCHAR(100), -- analysis, prediction, recommendation, report
    input_data TEXT,
    output_data TEXT,
    execution_time_ms INTEGER,
    status VARCHAR(50), -- success, error, partial
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_logs_agent ON agent_logs(agent_name);
CREATE INDEX idx_agent_logs_project ON agent_logs(project_id);
CREATE INDEX idx_agent_logs_type ON agent_logs(execution_type);
CREATE INDEX idx_agent_logs_created ON agent_logs(created_at);

-- ============================================
-- CONVERSATION HISTORY
-- ============================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    project_id UUID REFERENCES projects(id),
    session_id UUID NOT NULL,
    message TEXT NOT NULL,
    role VARCHAR(50) NOT NULL, -- user, assistant
    context TEXT, -- JSON with conversation context
    citations TEXT, -- JSON with data citations
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_project ON conversations(project_id);
CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_created ON conversations(created_at);

-- ============================================
-- SYSTEM LOGS
-- ============================================

CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL, -- debug, info, warning, error, critical
    component VARCHAR(100), -- api, agent, database, scheduler
    message TEXT NOT NULL,
    details TEXT,
    user_id UUID REFERENCES users(id),
    ip_address VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_component ON system_logs(component);
CREATE INDEX idx_system_logs_created ON system_logs(created_at);

-- ============================================
-- FUNCTIONS AND TRIGGERS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_schedules_updated_at BEFORE UPDATE ON schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_activities_updated_at BEFORE UPDATE ON activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON suppliers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_materials_updated_at BEFORE UPDATE ON materials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_purchase_orders_updated_at BEFORE UPDATE ON purchase_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_purchase_order_items_updated_at BEFORE UPDATE ON purchase_order_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_risks_updated_at BEFORE UPDATE ON risks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recommendations_updated_at BEFORE UPDATE ON recommendations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_memory_updated_at BEFORE UPDATE ON agent_memory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VIEWS
-- ============================================

-- View for project summary
CREATE VIEW project_summary AS
SELECT 
    p.id,
    p.name,
    p.code,
    p.status,
    p.progress_percentage,
    p.start_date,
    p.planned_end_date,
    p.actual_end_date,
    ph.overall_health_score,
    ph.schedule_health_score,
    ph.procurement_health_score,
    ph.risk_score,
    ph.open_risks_count,
    ph.critical_risks_count,
    COUNT(DISTINCT s.id) as total_schedules,
    COUNT(DISTINCT po.id) as total_purchase_orders
FROM projects p
LEFT JOIN project_health ph ON p.id = ph.project_id AND ph.metric_date = (
    SELECT MAX(metric_date) FROM project_health WHERE project_id = p.id
)
LEFT JOIN schedules s ON p.id = s.project_id
LEFT JOIN purchase_orders po ON p.id = po.project_id
GROUP BY p.id, ph.overall_health_score, ph.schedule_health_score, 
         ph.procurement_health_score, ph.risk_score, ph.open_risks_count, 
         ph.critical_risks_count;

-- View for supplier performance summary
CREATE VIEW supplier_summary AS
SELECT 
    s.id,
    s.supplier_code,
    s.name,
    s.category,
    s.rating,
    s.total_orders,
    s.on_time_delivery_rate,
    s.quality_score,
    COUNT(DISTINCT po.id) as active_orders,
    SUM(CASE WHEN po.status = 'delivered' THEN 1 ELSE 0 END) as completed_orders
FROM suppliers s
LEFT JOIN purchase_orders po ON s.id = po.supplier_id AND po.status IN ('pending', 'approved', 'ordered', 'shipped')
GROUP BY s.id;

-- View for critical activities
CREATE VIEW critical_activities AS
SELECT 
    a.id,
    a.activity_id,
    a.activity_name,
    a.schedule_id,
    s.project_id,
    a.early_start,
    a.early_finish,
    a.percent_complete,
    a.remaining_duration,
    cp.is_bottleneck,
    cp.total_float
FROM activities a
JOIN schedules s ON a.schedule_id = s.id
JOIN critical_path cp ON a.id = cp.activity_id
WHERE a.is_critical = true
AND cp.calculation_date = (
    SELECT MAX(calculation_date) FROM critical_path WHERE schedule_id = a.schedule_id
);

-- ============================================
-- INITIAL DATA
-- ============================================

-- Insert default admin user (password: Admin@123 - should be changed in production)
INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified) VALUES
('admin@aimonitor.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7bNqZjxqK6', 'System', 'Administrator', 'admin', true);

-- ============================================
-- GRANTS
-- ============================================

-- Grant necessary permissions (adjust based on your security requirements)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
