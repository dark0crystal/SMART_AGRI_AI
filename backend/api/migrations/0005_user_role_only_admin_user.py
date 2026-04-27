# Generated manually: catalog only user + admin roles.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0004_replace_lemon_catalog_with_model_classes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("user", "user"), ("admin", "admin")],
                default="user",
                max_length=20,
            ),
        ),
    ]
