from django.db import migrations


def fix_admin_log_user_foreign_key(apps, schema_editor):
    LogEntry = apps.get_model('admin', 'LogEntry')
    CustomUser = apps.get_model('easy_kart', 'CustomUser')
    user_field = LogEntry._meta.get_field('user')
    expected_foreign_key = (CustomUser._meta.db_table, CustomUser._meta.pk.column)

    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(
            cursor,
            LogEntry._meta.db_table,
        )

    current_foreign_keys = {
        constraint['foreign_key']
        for constraint in constraints.values()
        if constraint.get('columns') == [user_field.column]
        and constraint.get('foreign_key')
    }
    if expected_foreign_key in current_foreign_keys:
        return

    old_field = user_field.clone()
    old_field.remote_field.model = apps.get_model('auth', 'User')
    old_field.set_attributes_from_name(user_field.name)
    old_field.model = LogEntry
    schema_editor.alter_field(LogEntry, old_field, user_field, strict=False)


class Migration(migrations.Migration):

    dependencies = [
        ('admin', '0003_logentry_add_action_flag_choices'),
        ('easy_kart', '0035_registrationotp_alter_customuser_email_otp_code'),
    ]

    operations = [
        migrations.RunPython(fix_admin_log_user_foreign_key, migrations.RunPython.noop),
    ]
