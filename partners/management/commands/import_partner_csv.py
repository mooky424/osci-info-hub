import csv
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from partners.models import Contact, Needs, Partner, PastInterventions, SocioEconomicProfile
from users.models import User


class Command(BaseCommand):
    help = "Import partners, contacts, needs, profiles, and interventions from one CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and parse rows without saving",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]

        required_columns = {
            "partner_name",
            "partner_date_established",
            "partner_sec_registration",
            "partner_bir_registration",
            "partner_tin",
        }

        counters = {
            "rows": 0,
            "errors": 0,
            "partners_created": 0,
            "partners_updated": 0,
            "contacts_created": 0,
            "contacts_updated": 0,
            "needs_created": 0,
            "needs_updated": 0,
            "profiles_created": 0,
            "profiles_updated": 0,
            "interventions_created": 0,
            "interventions_updated": 0,
        }

        with open(csv_path, newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames:
                raise CommandError("CSV has no header row.")

            missing = sorted(required_columns - set(reader.fieldnames))
            if missing:
                raise CommandError(
                    f"Missing required CSV columns: {', '.join(missing)}"
                )

            current_partner_key = None

            with transaction.atomic():
                for row_number, row in enumerate(reader, start=2):
                    counters["rows"] += 1
                    try:
                        row_result, current_partner_key = self._import_row(
                            row,
                            current_partner_key,
                        )
                    except Exception as exc:
                        counters["errors"] += 1
                        self.stdout.write(
                            self.style.ERROR(f"Row {row_number}: {exc}")
                        )
                        continue

                    for key, value in row_result.items():
                        counters[key] += value

                if dry_run:
                    transaction.set_rollback(True)

        mode = "Dry run" if dry_run else "Import"
        self.stdout.write(self.style.SUCCESS(f"{mode} completed."))
        for key, value in counters.items():
            self.stdout.write(f"{key}: {value}")

    def _import_row(self, row, current_partner_key):
        result = {
            "partners_created": 0,
            "partners_updated": 0,
            "contacts_created": 0,
            "contacts_updated": 0,
            "needs_created": 0,
            "needs_updated": 0,
            "profiles_created": 0,
            "profiles_updated": 0,
            "interventions_created": 0,
            "interventions_updated": 0,
        }

        partner_name = _value(row, "partner_name")
        partner_date_established_raw = _value(row, "partner_date_established")
        partner_sec_registration = _value(row, "partner_sec_registration")
        partner_bir_registration = _value(row, "partner_bir_registration")
        partner_tin = _value(row, "partner_tin")

        partner_identifiers = [
            partner_name,
            partner_date_established_raw,
            partner_sec_registration,
            partner_bir_registration,
            partner_tin,
        ]
        provided_identifiers = [value for value in partner_identifiers if value]

        if provided_identifiers and len(provided_identifiers) != len(partner_identifiers):
            raise ValueError(
                "Partner identity columns must be all filled or all blank: "
                "partner_name, partner_date_established, partner_sec_registration, "
                "partner_bir_registration, partner_tin"
            )

        if not provided_identifiers:
            if current_partner_key is None:
                raise ValueError(
                    "Missing partner identity and no previous partner row to reuse"
                )
            partner_name = current_partner_key["name"]
            date_established = current_partner_key["date_established"]
            partner_sec_registration = current_partner_key["sec_registration"]
            partner_bir_registration = current_partner_key["bir_registration"]
            partner_tin = current_partner_key["tin"]
            update_partner_profile = False
        else:
            date_established = _date(
                partner_date_established_raw,
                "partner_date_established",
            )
            update_partner_profile = True

        partner_defaults = {
            "vision": _value(row, "partner_vision"),
            "mission": _value(row, "partner_mission"),
            "goals": _value(row, "partner_goals"),
            "description": _value(row, "partner_description"),
            "core_values": _value(row, "partner_core_values"),
            "sec_registration": partner_sec_registration,
            "bir_registration": partner_bir_registration,
            "tin": partner_tin,
            "moa_start_date": _date(
                _value(row, "partner_moa_start_date"), "partner_moa_start_date"
            ),
            "moa_end_date": _date(
                _value(row, "partner_moa_end_date"), "partner_moa_end_date"
            ),
            "moa_link": _value(row, "partner_moa_link"),
            "is_archived": False,
        }

        if update_partner_profile:
            partner, created = Partner.objects.update_or_create(
                name=partner_name,
                date_established=date_established,
                defaults=partner_defaults,
            )
        else:
            partner = Partner.objects.get(
                name=partner_name,
                date_established=date_established,
            )
            created = False
        if update_partner_profile:
            result["partners_created" if created else "partners_updated"] += 1

        contact_name = _value(row, "contact_name")
        if contact_name:
            contact_defaults = {
                "contact_number": _required(row, "contact_number"),
                "email": _value(row, "contact_email"),
            }
            _, created = Contact.objects.update_or_create(
                community_partner=partner,
                name=contact_name,
                position=_required(row, "contact_position"),
                defaults=contact_defaults,
            )
            result["contacts_created" if created else "contacts_updated"] += 1

        need_name = _value(row, "need_name")
        if need_name:
            need_defaults = {
                "description": _value(row, "need_description"),
                "objectives": _value(row, "need_objectives"),
                "expected_outcomes": _value(row, "need_expected_outcomes"),
                "skills_needed": _value(row, "need_skills_needed"),
                "is_archived": False,
            }
            _, created = Needs.objects.update_or_create(
                community_partner=partner,
                name=need_name,
                defaults=need_defaults,
            )
            result["needs_created" if created else "needs_updated"] += 1

        profile_population_size = _value(row, "profile_population_size")
        if profile_population_size:
            profile_defaults = {
                "population_size": _int(profile_population_size, "profile_population_size"),
                "population_breakdown": _value(row, "profile_population_breakdown"),
                "livelihoods": _value(row, "profile_livelihoods"),
                "health_profile": _value(row, "profile_health_profile"),
                "sociocultural_profile": _value(row, "profile_sociocultural_profile"),
                "political_profile": _value(row, "profile_political_profile"),
                "partner_networks": _value(row, "profile_partner_networks"),
                "resources_available": _value(row, "profile_resources_available"),
                "vulnerabilities": _value(row, "profile_vulnerabilities"),
                "housing": _value(row, "profile_housing"),
                "transportation": _value(row, "profile_transportation"),
                "electricity": _value(row, "profile_electricity"),
                "water": _value(row, "profile_water"),
                "wet_market": _value(row, "profile_wet_market"),
                "health_facilities": _value(row, "profile_health_facilities"),
                "education_facility": _value(row, "profile_education_facility"),
                "telecommunication": _value(row, "profile_telecommunication"),
                "others": _value(row, "profile_others"),
            }
            _, created = SocioEconomicProfile.objects.update_or_create(
                community_partner=partner,
                defaults=profile_defaults,
            )
            result["profiles_created" if created else "profiles_updated"] += 1

        intervention_name = _value(row, "intervention_name")
        if intervention_name:
            formator = None
            formator_username = _value(row, "intervention_formator_username")
            if formator_username:
                formator = User.objects.filter(username=formator_username).first()

            date_started = _date(
                _required(row, "intervention_date_started"),
                "intervention_date_started",
            )

            intervention_defaults = {
                "description": _value(row, "intervention_description"),
                "outcomes": _value(row, "intervention_outcomes"),
                "formator": formator,
                "date_ended": _date(
                    _value(row, "intervention_date_ended"),
                    "intervention_date_ended",
                ),
                "output_link": _value(row, "intervention_output_link"),
                "pictures_link": _value(row, "intervention_pictures_link"),
                "evaluation_link": _value(row, "intervention_evaluation_link"),
                "is_archived": False,
            }

            _, created = PastInterventions.objects.update_or_create(
                community_partner=partner,
                name=intervention_name,
                date_started=date_started,
                defaults=intervention_defaults,
            )
            result[
                "interventions_created" if created else "interventions_updated"
            ] += 1

        current_partner_key = {
            "name": partner.name,
            "date_established": partner.date_established,
            "sec_registration": partner.sec_registration,
            "bir_registration": partner.bir_registration,
            "tin": partner.tin,
        }

        return result, current_partner_key


def _value(row, key):
    raw = row.get(key, "")
    return raw.strip() if isinstance(raw, str) else ""


def _required(row, key):
    value = _value(row, key)
    if not value:
        raise ValueError(f"Missing required field: {key}")
    return value


def _date(value, field_name):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date for {field_name}: {value}") from exc


def _int(value, field_name):
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {field_name}: {value}") from exc



