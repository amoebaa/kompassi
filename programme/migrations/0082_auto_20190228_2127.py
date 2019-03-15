# Generated by Django 2.1.5 on 2019-02-28 19:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programme', '0081_auto_20190226_2021'),
    ]

    operations = [
        migrations.AddField(
            model_name='programme',
            name='content_warnings',
            field=models.CharField(blank=True, default='', help_text='If your program contains heavy topics or potentially distressing themes, please mention it here.', max_length=1023, verbose_name='Content warnings'),
        ),
        migrations.AlterField(
            model_name='programme',
            name='ropecon2019_blocked_time_slots',
            field=models.ManyToManyField(blank=True, help_text="When are you <strong>unable to run</strong> your game?<br><br>Tell us when you <strong>can not run</strong> your game. You can write more specific requests in the <em>other information</em> field below (e.g. <em>I'd like to run my game late in the evening</em>), but here we want information about limitations set by for example work or bus schedules (for example if you need to leave the venue by 11 PM to get to your accommodation in time).", to='ropecon2019.TimeSlot', verbose_name='time preferences'),
        ),
    ]