from django.core.management.base import BaseCommand

from users.models import User


DEFAULT_USERS = [
    {
        "username": "admin1",
        "email": "admin1@example.com",
        "name": "Admin One",
        "role": User.Role.ADMINISTRATOR,
        "password": "admin12345",
    },
    {
        "username": "admin2",
        "email": "admin2@example.com",
        "name": "Admin Two",
        "role": User.Role.ADMINISTRATOR,
        "password": "admin12345",
    },
]


class Command(BaseCommand):
    help = "Seed two administrator users"

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for user_data in DEFAULT_USERS:
            username = user_data["username"]
            password = user_data["password"]

            defaults = {
                "email": user_data["email"],
                "name": user_data["name"],
                "role": user_data["role"],
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            }

            user, created = User.objects.get_or_create(
                username=username, defaults=defaults
            )

            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
                created_count += 1
            else:
                changed = False
                for field, value in defaults.items():
                    if getattr(user, field) != value:
                        setattr(user, field, value)
                        changed = True
                if changed:
                    user.save(update_fields=list(defaults.keys()))
                    updated_count += 1
                if not user.check_password(password):
                    user.set_password(password)
                    user.save(update_fields=["password"])
                    updated_count += 1

            self.stdout.write(
                self.style.SUCCESS(f"User ready: {username} (password: {password})")
            )

        self.stdout.write(self.style.SUCCESS("User seeding completed."))
        self.stdout.write(f"Users created: {created_count}")
        self.stdout.write(f"Users updated: {updated_count}")
