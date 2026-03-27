from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from partners.models import Partner, PartnerStatus
from programs.models import AreaEngagement, EngagementTransportation, Section


class Command(BaseCommand):
    help = "Seed minimal demo data for programs"

    def handle(self, *args, **options):
        User = get_user_model()

        formator, _ = User.objects.get_or_create(
            username="formator",
            defaults={"role": "Formator"},
        )
        if not formator.has_usable_password():
            formator.set_password("password")
            formator.save(update_fields=["password"])

        staff, _ = User.objects.get_or_create(
            username="staff",
            defaults={"role": "OSCI Staff"},
        )
        if not staff.has_usable_password():
            staff.set_password("password")
            staff.save(update_fields=["password"])

        partners = [
            (
                "Bayanihan Health Network",
                "BHN",
                "BHN-001",
                "Health",
                "Barangay San Isidro, Quezon City",
                "09123456789",
            ),
            (
                "Green Steps Collective",
                "GSC",
                "GSC-014",
                "Environment",
                "Marikina River Park, Marikina",
                "09987654321",
            ),
            (
                "Ateneo Learning Partners",
                "ALP",
                "ALP-203",
                "Education",
                "Katipunan Ave, Quezon City",
                "09011223344",
            ),
        ]

        partner_objs: list[Partner] = []
        for name, acronym, area_code, sector, address, contact_no in partners:
            p, _ = Partner.objects.get_or_create(
                area_code=area_code,
                defaults={
                    "name": name,
                    "acronym": acronym,
                    "sector": sector,
                    "description": "",
                    "address": address,
                    "google_maps_link": "",
                    "ncr_or_province": "NCR+",
                    "point_person": "Juan Dela Cruz",
                    "head_of_office": "Maria Santos",
                    "contact_no": contact_no,
                    "contact_email": "",
                },
            )
            partner_objs.append(p)

        today = timezone.now().date()
        status_rows = [
            (partner_objs[0], "Active", today - timedelta(days=7)),
            (partner_objs[1], "On Hold", today - timedelta(days=3)),
            (partner_objs[2], "Inactive", today - timedelta(days=10)),
        ]
        for partner, status, when in status_rows:
            exists = PartnerStatus.objects.filter(
                partner=partner, status=status
            ).exists()
            if exists:
                continue
            PartnerStatus.objects.create(
                partner=partner,
                status=status,
                updated_by=staff,
                date=when,
            )

        sections = [
            (
                "AY 2025-2026",
                "2nd Sem",
                "NSTP 11",
                "A",
                "Faber Hall",
                "Prof. A. Rivera",
                "TTh 10:00-11:30",
                36,
            ),
            (
                "AY 2025-2026",
                "2nd Sem",
                "NSTP 11",
                "B",
                "Faber Hall",
                "Prof. L. Cruz",
                "MW 13:00-14:30",
                40,
            ),
            (
                "AY 2025-2026",
                "2nd Sem",
                "NSTP 12",
                "C",
                "Berchmans",
                "Prof. J. Lim",
                "Sat 09:00-12:00",
                32,
            ),
        ]

        section_objs: list[Section] = []
        for (
            ay,
            sem,
            course,
            sec,
            classroom,
            faculty,
            schedule,
            num_students,
        ) in sections:
            s, _ = Section.objects.get_or_create(
                academic_year=ay,
                semester=sem,
                course=course,
                section=sec,
                defaults={
                    "classroom": classroom,
                    "faculty": faculty,
                    "schedule": schedule,
                    "num_students": num_students,
                },
            )
            section_objs.append(s)

        base_dt = timezone.now().replace(minute=0, second=0, microsecond=0) + timedelta(
            days=2
        )

        engagements = [
            (section_objs[0], partner_objs[0], "Binhi", "2-day Live Out", 1),
            (section_objs[1], partner_objs[1], "Punla", "3-day Live Out", 2),
            (section_objs[2], partner_objs[2], "Bigkis", "Stay In", 1),
        ]

        for sec, partner, program_type, mode, week in engagements:
            ae, created = AreaEngagement.objects.get_or_create(
                section=sec,
                partner=partner,
                week=week,
                start_date=today + timedelta(days=7 + (week - 1) * 7),
                end_date=today + timedelta(days=13 + (week - 1) * 7),
                defaults={
                    "formator": formator,
                    "type": program_type,
                    "mode": mode,
                    "status": "Go",
                    "num_slots": 40,
                    "num_groups": 8,
                    "max_members_per_group": 5,
                    "num_deputies_needed": 2,
                    "special_remarks": "",
                    "course_orientation": base_dt,
                    "binhi_orientation": base_dt + timedelta(days=3),
                    "binhi_orientation_venue": "MVP 101",
                    "integration_session": base_dt + timedelta(days=10),
                    "integration_session_venue": "Room 204",
                    "area_engagement_assembly": base_dt + timedelta(days=14),
                    "processing_session": base_dt + timedelta(days=21),
                    "processing_session_venue": "Zoom",
                    "integration_presentation": base_dt + timedelta(days=28),
                },
            )
            if not created:
                ae.formator = formator
                ae.type = program_type
                ae.mode = mode
                ae.status = "Go"
                ae.save(update_fields=["formator", "type", "mode", "status"])

            ae.deputies.add(staff)

            EngagementTransportation.objects.get_or_create(
                area_engagement=ae,
                defaults={
                    "mode_of_transportation": "Van",
                    "duration_days": 1,
                    "total_passengers": 16,
                    "num_vehicles_needed": 1,
                    "km_two_way": 24,
                    "driver_assembly_time": time(7, 30),
                    "admu_arrival_time": time(18, 0),
                    "meetup_place": "Gate 3",
                },
            )

        self.stdout.write(self.style.SUCCESS("Seeded programs demo data."))
