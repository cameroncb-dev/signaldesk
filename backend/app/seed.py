from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Asset, Ticket


ASSIGNMENT_GROUPS = [
    {
        "name": "Fiber Operations",
        "focus": "Optical transport, OTDR alarms, span cuts, metro rings",
    },
    {
        "name": "Wireless RAN",
        "focus": "Cell sites, 5G mid-band capacity, radios, backhaul",
    },
    {
        "name": "Core Network",
        "focus": "BGP, peering, routers, SIP trunks, voice core",
    },
    {
        "name": "Digital Experience",
        "focus": "Customer-facing APIs, billing, self-service apps",
    },
    {
        "name": "IT Service Management",
        "focus": "ServiceNow integrations, workflow automation, CMDB",
    },
    {
        "name": "Cloud Platform",
        "focus": "Azure landing zones, identity, platform reliability",
    },
]


def _ticket(**kwargs) -> Ticket:
    opened = kwargs.pop("opened_at", datetime.utcnow())
    return Ticket(
        sys_id=str(uuid4()),
        opened_at=opened,
        updated_at=opened,
        **kwargs,
    )


def seed_if_empty(db: Session) -> None:
    if db.query(Asset).first():
        return

    assets = [
        Asset(
            ci_id="FS-DFW-014",
            name="DFW metro fiber span 014",
            kind="fiber_span",
            region="Dallas-Fort Worth",
            owner_group="Fiber Operations",
            status="degraded",
            details="144-count metro ring. Last OTDR showed 4.2 dB loss at 18.6 km.",
        ),
        Asset(
            ci_id="CS-ATL-221",
            name="Atlanta downtown cell site 221",
            kind="cell_site",
            region="Atlanta",
            owner_group="Wireless RAN",
            status="degraded",
            details="n77 mid-band. PRB utilization 94%. Backhaul on FS-ATL-008.",
        ),
        Asset(
            ci_id="API-BILL-PROD",
            name="Billing API production",
            kind="application",
            region="Azure East US",
            owner_group="Digital Experience",
            status="impaired",
            details="Public REST API behind APIM. Error budget burn 2.1x after Friday deploy.",
        ),
        Asset(
            ci_id="INT-SNOW-HR",
            name="ServiceNow HR integration",
            kind="integration",
            region="Azure East US",
            owner_group="IT Service Management",
            status="impaired",
            details="Table API consumer. Timeouts started after mid-tier cert rotation.",
        ),
        Asset(
            ci_id="CR-CHI-01",
            name="Chicago core router 01",
            kind="core_router",
            region="Chicago",
            owner_group="Core Network",
            status="operational",
            details="Peering edge. Historical BGP flaps during IX maintenance windows.",
        ),
        Asset(
            ci_id="LH-DAL-MIA",
            name="Dallas-Miami long-haul",
            kind="optical_route",
            region="South Central",
            owner_group="Fiber Operations",
            status="operational",
            details="100G DWDM wave. Prior OTDR events correlated with construction permits.",
        ),
    ]
    db.add_all(assets)

    now = datetime.utcnow()
    tickets = [
        _ticket(
            number="INC0010041",
            short_description="OTDR alarm and packet loss on DFW metro fiber span",
            description=(
                "NOC received an OTDR critical alarm on FS-DFW-014 at 18:12 CT. "
                "Enterprise ethernet customers in Plano and Irving are seeing 8-12% packet loss. "
                "Field reports construction near the 18 km marker. Need triage, customer comms, "
                "and a dispatch recommendation."
            ),
            urgency=1,
            impact=1,
            priority=1,
            state="new",
            category="network",
            cmdb_ci="FS-DFW-014",
            caller="NOC Night Shift",
            opened_at=now - timedelta(minutes=22),
        ),
        _ticket(
            number="INC0010042",
            short_description="5G mid-band capacity drop at Atlanta downtown site",
            description=(
                "CS-ATL-221 PRB utilization spiked to 94% after a concert let out. "
                "Users reporting buffering on video and failed 5G SA attach. "
                "Can we temporarily rehome load or authorize a small cell overlay?"
            ),
            urgency=1,
            impact=2,
            priority=2,
            state="new",
            category="wireless",
            cmdb_ci="CS-ATL-221",
            caller="RAN Watch",
            opened_at=now - timedelta(hours=1, minutes=5),
        ),
        _ticket(
            number="INC0010043",
            short_description="Billing API 5xx after Friday production deploy",
            description=(
                "API-BILL-PROD error rate jumped from 0.3% to 7.8% after release 2026.9.19. "
                "Checkout and usage-to-cash jobs are failing. Azure APIM shows upstream 504s. "
                "Need rollback vs. hotfix decision and a customer-safe status update."
            ),
            urgency=1,
            impact=1,
            priority=1,
            state="new",
            category="application",
            cmdb_ci="API-BILL-PROD",
            caller="Digital SRE",
            opened_at=now - timedelta(hours=3),
        ),
        _ticket(
            number="INC0010044",
            short_description="ServiceNow Table API timeouts after cert rotation",
            description=(
                "INT-SNOW-HR started returning 401/timeouts after last night's mid-tier cert rotation. "
                "HR case sync is queued. This is blocking onboarding workflows that depend on "
                "the ServiceNow integration."
            ),
            urgency=2,
            impact=2,
            priority=3,
            state="new",
            category="integration",
            cmdb_ci="INT-SNOW-HR",
            caller="ITSM Platform",
            opened_at=now - timedelta(hours=6),
        ),
        _ticket(
            number="INC0010028",
            short_description="Resolved: DFW fiber cut from construction bore",
            description=(
                "Historical incident. Construction bore severed FS-DFW-014 near 18.4 km. "
                "Traffic failed west, fiber ops spliced overnight, customers restored."
            ),
            urgency=1,
            impact=1,
            priority=1,
            state="resolved",
            category="network",
            subcategory="fiber_cut",
            assignment_group="Fiber Operations",
            assigned_to="Jordan Hale",
            cmdb_ci="FS-DFW-014",
            caller="NOC Day Shift",
            work_notes="Dispatch recommended. Similar OTDR signature to 2025 Q4 bore events.",
            close_notes="Splice completed. Monitoring 24h. Construction permit logged.",
            opened_at=now - timedelta(days=40),
        ),
        _ticket(
            number="INC0010019",
            short_description="Resolved: Billing API regression after schema change",
            description=(
                "Historical incident. Usage endpoint started 500ing after a breaking schema change. "
                "Rolled back APIM revision and patched contract tests."
            ),
            urgency=1,
            impact=1,
            priority=1,
            state="resolved",
            category="application",
            subcategory="regression",
            assignment_group="Digital Experience",
            assigned_to="Priya Shah",
            cmdb_ci="API-BILL-PROD",
            caller="Digital SRE",
            close_notes="Rollback + contract test gate added to pipeline.",
            opened_at=now - timedelta(days=71),
        ),
        _ticket(
            number="INC0010033",
            short_description="Resolved: Chicago BGP flap during IX maintenance",
            description="CR-CHI-01 withdrew prefixes during planned IX maintenance. Re-advertised after window.",
            urgency=2,
            impact=2,
            priority=3,
            state="resolved",
            category="network",
            subcategory="bgp",
            assignment_group="Core Network",
            cmdb_ci="CR-CHI-01",
            caller="Core On-call",
            opened_at=now - timedelta(days=18),
        ),
        _ticket(
            number="INC0010037",
            short_description="Long-haul OTDR event Dallas-Miami, no customer impact yet",
            description=(
                "LH-DAL-MIA reported a transient OTDR reflection. No SLA burn. "
                "Want a watch-and-see vs. proactive patrol recommendation."
            ),
            urgency=3,
            impact=3,
            priority=4,
            state="new",
            category="network",
            cmdb_ci="LH-DAL-MIA",
            caller="Optical Transport",
            opened_at=now - timedelta(hours=9),
        ),
    ]
    db.add_all(tickets)
    db.commit()
