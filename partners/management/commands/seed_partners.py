from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from partners.models import (
    Contact,
    Partner,
    PastInterventions,
    Programs,
    SocioEconomicProfile,
)
from users.models import User


class Command(BaseCommand):
    help = "Seed partner data (around 3 records)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=3,
            help="Number of partners to seed (default: 3)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = max(1, options["count"])

        formator, _ = User.objects.get_or_create(
            username="seed.formator",
            defaults={
                "first_name": "Seed",
                "last_name": "Formator",
                "email": "seed.formator@example.com",
                "role": User.Role.ADMINISTRATOR,
                "name": "Seed Formator",
                "position": "Program Formator",
            },
        )

        if not formator.has_usable_password():
            formator.set_password("seedpassword123")
            formator.save(update_fields=["password"])

        created_partners = 0
        created_contacts = 0
        created_profiles = 0
        created_programs = 0
        created_interventions = 0

        for idx in range(1, count + 1):
            partner_name = f"Seed Partner {idx}"
            partner, created = Partner.objects.get_or_create(
                name=partner_name,
                defaults={
                    "vision": f"Vision statement for {partner_name}.",
                    "mission": f"Mission statement for {partner_name}.",
                    "goals": f"Key goals for {partner_name}.",
                    "description": f"Profile description for {partner_name}.",
                    "core_values": "Integrity, Service, Collaboration",
                    "date_established": date(2010 + idx, 1, min(idx, 28)),
                    "sec_registration": f"SEC-{idx:04d}",
                    "bir_registration": f"BIR-{idx:04d}",
                    "tin": f"{200000000 + idx}",
                    "moa_start_date": date.today() - timedelta(days=365 * (idx + 1)),
                    "moa_end_date": date.today()
                    + timedelta(days=365 * (3 - min(idx, 3))),
                    "moa_link": f"https://example.com/moa/seed-partner-{idx}",
                    "updated_by": formator,
                },
            )

            if created:
                created_partners += 1

            contact, contact_created = Contact.objects.get_or_create(
                community_partner=partner,
                name=f"Contact Person {idx}",
                defaults={
                    "position": "Program Coordinator",
                    "designation": "Primary Contact",
                    "contact_number": f"09{idx:09d}",
                    "email": f"partner{idx}@example.com",
                },
            )
            if contact_created:
                created_contacts += 1

            profile, profile_created = SocioEconomicProfile.objects.get_or_create(
                community_partner=partner,
                defaults={
                    "population_size": 1000 * idx,
                    "population_breakdown": "Mixed working-age population",
                    "livelihoods": "Farming, microenterprise, services",
                    "health_profile": "Common respiratory and nutrition concerns",
                    "sociocultural_profile": "Community-led organizations are active",
                    "political_profile": "Barangay and municipal coordination in place",
                    "partner_networks": "LGU, schools, local CSOs",
                    "resources_available": "Community hall, volunteers, local transport",
                    "vulnerabilities": "Flood-prone areas and seasonal unemployment",
                    "housing": "Mostly permanent mixed-material homes",
                    "transportation": "Jeepney and tricycle routes",
                    "electricity": "Grid-connected",
                    "water": "Mixed piped and communal sources",
                    "wet_market": "Within 2-3 km",
                    "health_facilities": "Barangay health center",
                    "education_facility": "Public elementary and high school",
                    "telecommunication": "Mobile and broadband coverage",
                    "others": "Community radio and local watch groups",
                },
            )
            if profile_created:
                created_profiles += 1

            for prog_idx in range(1, 3):
                _, program_created = Programs.objects.get_or_create(
                    community_partner=partner,
                    name=f"Program {prog_idx} - {partner_name}",
                    defaults={
                        "description": "Program description",
                        "objectives": "Improve community participation",
                        "expected_outcomes": "Higher engagement and measurable outputs",
                        "skills_needed": "Facilitation, project management",
                    },
                )
                if program_created:
                    created_programs += 1

            for int_idx in range(1, 3):
                _, intervention_created = PastInterventions.objects.get_or_create(
                    community_partner=partner,
                    name=f"Intervention {int_idx} - {partner_name}",
                    defaults={
                        "description": "Intervention description",
                        "outcomes": "Documented positive outcomes",
                        "formator": formator,
                        "date_started": date.today() - timedelta(days=180 * int_idx),
                        "date_ended": date.today() - timedelta(days=120 * int_idx),
                        "output_link": f"https://example.com/output/{idx}-{int_idx}",
                        "pictures_link": f"https://example.com/pictures/{idx}-{int_idx}",
                        "evaluation_link": f"https://example.com/evaluation/{idx}-{int_idx}",
                    },
                )
                if intervention_created:
                    created_interventions += 1

        self.stdout.write(self.style.SUCCESS("Partner seeding completed."))
        self.stdout.write(f"Partners created: {created_partners}")
        self.stdout.write(f"Contacts created: {created_contacts}")
        self.stdout.write(f"Socioeconomic profiles created: {created_profiles}")
        self.stdout.write(f"Programs created: {created_programs}")
        self.stdout.write(f"Past interventions created: {created_interventions}")
