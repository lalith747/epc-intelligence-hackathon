"""
Demo data seeding for local development mode.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select

from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.models.database import (
    Activity,
    Dependency,
    Inventory,
    Material,
    Project,
    ProjectHealth,
    PurchaseOrder,
    PurchaseOrderItem,
    Recommendation,
    Report,
    Risk,
    Schedule,
    Supplier,
    User,
)
from app.services.database import AsyncSessionLocal

logger = get_logger(__name__)


async def seed_demo_data() -> None:
    """Create a realistic demo workspace for the single-host local app."""
    async with AsyncSessionLocal() as session:
        user_count = await session.scalar(select(func.count(User.id)))
        project_count = await session.scalar(select(func.count(Project.id)))

        if user_count or project_count:
            logger.info("Skipping demo seed because workspace data already exists")
            return

        today = date.today()
        start_date = today - timedelta(days=120)
        planned_end_date = today + timedelta(days=210)

        admin = User(
            id=str(uuid4()),
            email="admin@example.com",
            password_hash=get_password_hash("Admin@123"),
            first_name="Ava",
            last_name="Cole",
            role="admin",
            organization="Northstar EPC",
            phone="+44 20 7946 0958",
            is_active=True,
            is_verified=True,
            last_login=datetime.utcnow(),
        )
        session.add(admin)
        await session.flush()

        project = Project(
            id=str(uuid4()),
            name="Orion Data Centre Campus - Phase 1",
            code="ODC-P1",
            description="AI-monitored EPC delivery covering civil, MEP, power train, and commissioning packages.",
            client_name="Helios Cloud Infrastructure",
            location="Hyderabad, India",
            project_type="Data Centre EPC",
            contract_value=Decimal("185000000.00"),
            currency="EUR",
            start_date=start_date,
            planned_end_date=planned_end_date,
            total_budget=Decimal("162000000.00"),
            budget_consumed=Decimal("71100000.00"),
            status="execution",
            progress_percentage=Decimal("43.50"),
            owner_id=admin.id,
        )
        session.add(project)
        await session.flush()

        schedule = Schedule(
            id=str(uuid4()),
            project_id=project.id,
            name="Master EPC Schedule",
            version="v2026.07",
            source_type="primavera",
            baseline_date=start_date,
            data_date=today,
            total_activities=6,
        )
        session.add(schedule)
        await session.flush()

        activities = [
            Activity(
                id=str(uuid4()),
                schedule_id=schedule.id,
                activity_id="CIV-110",
                activity_name="Substructure and raft foundation",
                original_duration=55,
                remaining_duration=6,
                percent_complete=Decimal("92"),
                early_start=start_date,
                early_finish=start_date + timedelta(days=55),
                start_date=start_date,
                finish_date=start_date + timedelta(days=61),
                is_critical=True,
            ),
            Activity(
                id=str(uuid4()),
                schedule_id=schedule.id,
                activity_id="STL-210",
                activity_name="Structural steel and roof closure",
                original_duration=70,
                remaining_duration=19,
                percent_complete=Decimal("72"),
                early_start=start_date + timedelta(days=35),
                early_finish=start_date + timedelta(days=105),
                start_date=start_date + timedelta(days=38),
                finish_date=start_date + timedelta(days=118),
                is_critical=True,
            ),
            Activity(
                id=str(uuid4()),
                schedule_id=schedule.id,
                activity_id="MEP-320",
                activity_name="MEP first fix and cable tray installation",
                original_duration=90,
                remaining_duration=47,
                percent_complete=Decimal("46"),
                early_start=start_date + timedelta(days=80),
                early_finish=start_date + timedelta(days=170),
                start_date=start_date + timedelta(days=89),
                finish_date=start_date + timedelta(days=195),
                is_critical=True,
            ),
            Activity(
                id=str(uuid4()),
                schedule_id=schedule.id,
                activity_id="UPS-410",
                activity_name="UPS and switchgear delivery",
                original_duration=35,
                remaining_duration=24,
                percent_complete=Decimal("28"),
                early_start=start_date + timedelta(days=120),
                early_finish=start_date + timedelta(days=155),
                start_date=start_date + timedelta(days=126),
                finish_date=start_date + timedelta(days=171),
                is_critical=True,
            ),
            Activity(
                id=str(uuid4()),
                schedule_id=schedule.id,
                activity_id="CSA-470",
                activity_name="White space fit-out and containment",
                original_duration=65,
                remaining_duration=56,
                percent_complete=Decimal("14"),
                early_start=start_date + timedelta(days=150),
                early_finish=start_date + timedelta(days=215),
                is_critical=False,
            ),
            Activity(
                id=str(uuid4()),
                schedule_id=schedule.id,
                activity_id="COM-590",
                activity_name="Integrated systems testing and commissioning",
                original_duration=45,
                remaining_duration=45,
                percent_complete=Decimal("0"),
                early_start=start_date + timedelta(days=235),
                early_finish=start_date + timedelta(days=280),
                is_critical=True,
                is_milestone=True,
            ),
        ]
        session.add_all(activities)
        await session.flush()

        dependencies = [
            Dependency(
                id=str(uuid4()),
                schedule_id=schedule.id,
                predecessor_id=activities[0].id,
                successor_id=activities[1].id,
                dependency_type="finish_to_start",
                is_critical=True,
            ),
            Dependency(
                id=str(uuid4()),
                schedule_id=schedule.id,
                predecessor_id=activities[1].id,
                successor_id=activities[2].id,
                dependency_type="finish_to_start",
                is_critical=True,
            ),
            Dependency(
                id=str(uuid4()),
                schedule_id=schedule.id,
                predecessor_id=activities[2].id,
                successor_id=activities[3].id,
                dependency_type="finish_to_start",
                is_critical=True,
            ),
            Dependency(
                id=str(uuid4()),
                schedule_id=schedule.id,
                predecessor_id=activities[3].id,
                successor_id=activities[5].id,
                dependency_type="finish_to_start",
                is_critical=True,
            ),
        ]
        session.add_all(dependencies)

        suppliers = [
            Supplier(
                id=str(uuid4()),
                supplier_code="SUP-UPS-01",
                name="VoltGrid Systems",
                category="Electrical",
                contact_person="Marta Stein",
                email="marta@voltgrid.example",
                phone="+49 69 5550 1201",
                country="Germany",
                city="Frankfurt",
                rating=Decimal("4.30"),
                total_orders=8,
                on_time_delivery_rate=Decimal("74.00"),
                quality_score=Decimal("88.00"),
                is_preferred=True,
            ),
            Supplier(
                id=str(uuid4()),
                supplier_code="SUP-HVAC-02",
                name="ThermaCore Europe",
                category="Mechanical",
                contact_person="Jonas Weber",
                email="jonas@thermacore.example",
                phone="+49 40 8000 1144",
                country="Germany",
                city="Hamburg",
                rating=Decimal("4.60"),
                total_orders=11,
                on_time_delivery_rate=Decimal("92.00"),
                quality_score=Decimal("91.00"),
                is_preferred=True,
            ),
            Supplier(
                id=str(uuid4()),
                supplier_code="SUP-CBL-03",
                name="FiberSpan Industrial",
                category="Cable Infrastructure",
                contact_person="Rina Patel",
                email="rina@fiberspan.example",
                phone="+44 161 900 2211",
                country="United Kingdom",
                city="Manchester",
                rating=Decimal("3.90"),
                total_orders=6,
                on_time_delivery_rate=Decimal("69.00"),
                quality_score=Decimal("84.00"),
                is_preferred=False,
            ),
            Supplier(
                id=str(uuid4()),
                supplier_code="SUP-FAS-04",
                name="SecureSpark Controls",
                category="Fire and Security",
                contact_person="Anika Braun",
                email="anika@securespark.example",
                phone="+49 211 8877 0020",
                country="Germany",
                city="Dusseldorf",
                rating=Decimal("4.20"),
                total_orders=5,
                on_time_delivery_rate=Decimal("83.00"),
                quality_score=Decimal("89.00"),
                is_preferred=False,
            ),
        ]
        session.add_all(suppliers)
        await session.flush()

        materials = [
            Material(
                id=str(uuid4()),
                material_code="MAT-UPS-MOD",
                name="UPS Module 800kVA",
                category="Electrical Equipment",
                unit="ea",
                unit_cost=Decimal("42000.00"),
                lead_time=84,
            ),
            Material(
                id=str(uuid4()),
                material_code="MAT-CAB-11KV",
                name="11kV Power Cable",
                category="Cable",
                unit="m",
                unit_cost=Decimal("145.00"),
                lead_time=45,
            ),
            Material(
                id=str(uuid4()),
                material_code="MAT-CRAH-07",
                name="CRAH Unit",
                category="Mechanical",
                unit="ea",
                unit_cost=Decimal("18500.00"),
                lead_time=60,
            ),
        ]
        session.add_all(materials)
        await session.flush()

        inventory_records = [
            Inventory(
                id=str(uuid4()),
                project_id=project.id,
                material_id=materials[0].id,
                warehouse_location="Main Laydown Yard",
                quantity_on_hand=Decimal("1"),
                quantity_reserved=Decimal("1"),
                quantity_available=Decimal("0"),
                minimum_stock_level=Decimal("2"),
                reorder_point=Decimal("2"),
            ),
            Inventory(
                id=str(uuid4()),
                project_id=project.id,
                material_id=materials[1].id,
                warehouse_location="Cable Storage Zone A",
                quantity_on_hand=Decimal("1200"),
                quantity_reserved=Decimal("800"),
                quantity_available=Decimal("400"),
                minimum_stock_level=Decimal("750"),
                reorder_point=Decimal("900"),
            ),
            Inventory(
                id=str(uuid4()),
                project_id=project.id,
                material_id=materials[2].id,
                warehouse_location="MEP Warehouse",
                quantity_on_hand=Decimal("4"),
                quantity_reserved=Decimal("2"),
                quantity_available=Decimal("2"),
                minimum_stock_level=Decimal("2"),
                reorder_point=Decimal("3"),
            ),
        ]
        session.add_all(inventory_records)

        purchase_orders = [
            PurchaseOrder(
                id=str(uuid4()),
                project_id=project.id,
                po_number="PO-24017",
                supplier_id=suppliers[0].id,
                issue_date=today - timedelta(days=42),
                expected_delivery_date=today + timedelta(days=9),
                status="shipped",
                total_amount=Decimal("336000.00"),
                currency="EUR",
                priority="high",
            ),
            PurchaseOrder(
                id=str(uuid4()),
                project_id=project.id,
                po_number="PO-24022",
                supplier_id=suppliers[2].id,
                issue_date=today - timedelta(days=31),
                expected_delivery_date=today - timedelta(days=3),
                actual_delivery_date=None,
                status="ordered",
                total_amount=Decimal("652500.00"),
                currency="EUR",
                priority="high",
            ),
            PurchaseOrder(
                id=str(uuid4()),
                project_id=project.id,
                po_number="PO-24031",
                supplier_id=suppliers[1].id,
                issue_date=today - timedelta(days=52),
                expected_delivery_date=today - timedelta(days=4),
                actual_delivery_date=today - timedelta(days=2),
                status="delivered",
                total_amount=Decimal("148000.00"),
                currency="EUR",
                priority="normal",
            ),
            PurchaseOrder(
                id=str(uuid4()),
                project_id=project.id,
                po_number="PO-24036",
                supplier_id=suppliers[3].id,
                issue_date=today - timedelta(days=12),
                expected_delivery_date=today + timedelta(days=18),
                status="pending",
                total_amount=Decimal("96000.00"),
                currency="EUR",
                priority="normal",
            ),
        ]
        session.add_all(purchase_orders)
        await session.flush()

        po_items = [
            PurchaseOrderItem(
                id=str(uuid4()),
                purchase_order_id=purchase_orders[0].id,
                material_id=materials[0].id,
                description="UPS Module 800kVA",
                quantity=Decimal("8"),
                unit="ea",
                unit_price=Decimal("42000.00"),
                total_price=Decimal("336000.00"),
                quantity_received=Decimal("0"),
                quantity_pending=Decimal("8"),
                status="shipped",
            ),
            PurchaseOrderItem(
                id=str(uuid4()),
                purchase_order_id=purchase_orders[1].id,
                material_id=materials[1].id,
                description="11kV Power Cable",
                quantity=Decimal("4500"),
                unit="m",
                unit_price=Decimal("145.00"),
                total_price=Decimal("652500.00"),
                quantity_received=Decimal("0"),
                quantity_pending=Decimal("4500"),
                status="ordered",
            ),
            PurchaseOrderItem(
                id=str(uuid4()),
                purchase_order_id=purchase_orders[2].id,
                material_id=materials[2].id,
                description="CRAH Unit",
                quantity=Decimal("8"),
                unit="ea",
                unit_price=Decimal("18500.00"),
                total_price=Decimal("148000.00"),
                quantity_received=Decimal("8"),
                quantity_pending=Decimal("0"),
                status="delivered",
            ),
        ]
        session.add_all(po_items)

        risks = [
            Risk(
                id=str(uuid4()),
                project_id=project.id,
                risk_code="RSK-SCH-001",
                title="Switchgear delivery threatens energisation path",
                description="Late electrical package delivery could push integrated testing by 18-24 days.",
                category="schedule",
                risk_source="schedule_analysis",
                probability=Decimal("78"),
                impact=Decimal("88"),
                risk_score=Decimal("68.64"),
                severity="high",
                confidence=Decimal("84"),
                status="open",
                identified_date=today - timedelta(days=4),
                owner_id=admin.id,
                related_activities=[activities[3].activity_id, activities[5].activity_id],
                related_suppliers=[suppliers[0].name],
                explanation="The UPS and switchgear package sits on the critical path and is behind promised shipping milestones.",
            ),
            Risk(
                id=str(uuid4()),
                project_id=project.id,
                risk_code="RSK-PRC-002",
                title="Cable shortage risk for MEP first fix",
                description="Current cable availability is below reorder point while two major installation fronts open this month.",
                category="procurement",
                risk_source="procurement_analysis",
                probability=Decimal("74"),
                impact=Decimal("81"),
                risk_score=Decimal("59.94"),
                severity="high",
                confidence=Decimal("79"),
                status="open",
                identified_date=today - timedelta(days=6),
                owner_id=admin.id,
                related_activities=[activities[2].activity_id],
                related_suppliers=[suppliers[2].name],
                explanation="Inventory coverage is lower than the planned installation burn rate and inbound cable delivery is already late.",
            ),
            Risk(
                id=str(uuid4()),
                project_id=project.id,
                risk_code="RSK-SUP-003",
                title="Vendor responsiveness slowing approval cycle",
                description="Submittal turnarounds from one package vendor remain slow and could delay release to site.",
                category="supplier",
                risk_source="supplier_performance",
                probability=Decimal("51"),
                impact=Decimal("55"),
                risk_score=Decimal("28.05"),
                severity="low",
                confidence=Decimal("66"),
                status="open",
                identified_date=today - timedelta(days=9),
                owner_id=admin.id,
                related_suppliers=[suppliers[3].name],
                explanation="Average response time over the last four transmittals exceeded contractual expectations.",
            ),
        ]
        session.add_all(risks)

        recommendations = [
            Recommendation(
                id=str(uuid4()),
                project_id=project.id,
                recommendation_code="REC-001",
                title="Split critical electrical package into expedited lots",
                description="Pull forward the first two UPS lots and route them through express customs clearance to protect energisation.",
                recommendation_type="expedite_delivery",
                expected_impact={"delay_reduction_days": 12, "confidence": 83},
                confidence=Decimal("83"),
                estimated_days_saved=12,
                estimated_cost_impact=Decimal("180000.00"),
                priority="high",
                status="pending",
                related_risks=[risks[0].risk_code],
                related_activities=[activities[3].activity_id, activities[5].activity_id],
                related_suppliers=[suppliers[0].name],
                explanation="Reduces single-point dependency on a full-batch delivery while protecting the critical path.",
                created_by_agent="recommendation_agent",
            ),
            Recommendation(
                id=str(uuid4()),
                project_id=project.id,
                recommendation_code="REC-002",
                title="Reallocate cable inventory from secondary zone",
                description="Transfer cable stock from non-critical fit-out work to the MEP first-fix area for the next 14 days.",
                recommendation_type="inventory_transfer",
                expected_impact={"delay_reduction_days": 6, "confidence": 79},
                confidence=Decimal("79"),
                estimated_days_saved=6,
                estimated_cost_impact=Decimal("24000.00"),
                priority="high",
                status="pending",
                related_risks=[risks[1].risk_code],
                related_activities=[activities[2].activity_id],
                related_suppliers=[suppliers[2].name],
                explanation="Buys installation continuity while the late cable order is being recovered.",
                created_by_agent="recommendation_agent",
            ),
            Recommendation(
                id=str(uuid4()),
                project_id=project.id,
                recommendation_code="REC-003",
                title="Add evening shift to MEP containment works",
                description="Introduce a six-week second shift to recover containment and support earlier equipment installation.",
                recommendation_type="extra_shift",
                expected_impact={"delay_reduction_days": 9, "confidence": 74},
                confidence=Decimal("74"),
                estimated_days_saved=9,
                estimated_cost_impact=Decimal("92000.00"),
                priority="medium",
                status="pending",
                related_activities=[activities[2].activity_id],
                explanation="Improves float on the critical path without changing engineering sequence.",
                created_by_agent="recommendation_agent",
            ),
        ]
        session.add_all(recommendations)

        reports = [
            Report(
                id=str(uuid4()),
                project_id=project.id,
                report_type="daily",
                report_name="Daily Executive Digest",
                report_date=today,
                generated_by_agent="executive_agent",
                content={
                    "headline": "Schedule pressure remains concentrated in electrical procurement.",
                    "highlights": [
                        "Overall health stable at low-70s",
                        "Two procurement-led risks require action this week",
                        "Recovery options could save up to 18 days",
                    ],
                },
                summary="The project remains viable but schedule exposure is increasing around electrical package deliveries and cable availability.",
                key_insights=[
                    "Critical path now runs through electrical energisation",
                    "Procurement recovery delivers the fastest benefit",
                ],
            ),
            Report(
                id=str(uuid4()),
                project_id=project.id,
                report_type="weekly",
                report_name="Weekly Management Report",
                report_date=today - timedelta(days=2),
                period_start=today - timedelta(days=8),
                period_end=today - timedelta(days=2),
                generated_by_agent="executive_agent",
                content={"status": "amber", "focus_area": "electrical procurement"},
                summary="Work fronts expanded, but material dependency risks increased faster than field productivity.",
                key_insights=[
                    "Schedule health fell 4 points week over week",
                    "Supplier delay exposure now affects commissioning readiness",
                ],
            ),
        ]
        session.add_all(reports)

        health_records = []
        for day_offset in range(14, -1, -1):
            metric_date = today - timedelta(days=day_offset)
            schedule_health = Decimal(str(74 - max(0, 14 - day_offset) * 0.45))
            procurement_health = Decimal(str(71 - max(0, 14 - day_offset) * 0.38))
            supplier_health = Decimal(str(78 - max(0, 14 - day_offset) * 0.30))
            risk_score = Decimal(str(41 + max(0, 14 - day_offset) * 0.95))
            completion = Decimal(str(37 + max(0, 14 - day_offset) * 0.45))
            overall = Decimal(
                str(
                    round(
                        float(schedule_health) * 0.35
                        + float(procurement_health) * 0.25
                        + float(supplier_health) * 0.20
                        + (100 - float(risk_score)) * 0.20,
                        2,
                    )
                )
            )
            health_records.append(
                ProjectHealth(
                    id=str(uuid4()),
                    project_id=project.id,
                    metric_date=metric_date,
                    overall_health_score=overall,
                    schedule_health_score=schedule_health,
                    procurement_health_score=procurement_health,
                    supplier_health_score=supplier_health,
                    risk_score=risk_score,
                    cost_performance_index=Decimal("0.97"),
                    schedule_performance_index=Decimal("0.91"),
                    completion_percentage=completion,
                    on_time_activities_percentage=Decimal(str(69 - max(0, 14 - day_offset) * 0.25)),
                    on_budget_percentage=Decimal("94"),
                    open_risks_count=3,
                    critical_risks_count=0,
                    open_recommendations_count=3,
                )
            )
        session.add_all(health_records)

        await session.commit()
        logger.info("Seeded demo admin user and project workspace")
