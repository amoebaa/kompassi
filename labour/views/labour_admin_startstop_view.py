# encoding: utf-8

from __future__ import unicode_literals

from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_http_methods

from core.utils import initialize_form

from ..helpers import labour_admin_required
from ..forms import StartStopForm


@labour_admin_required
def labour_admin_startstop_view(request, vars, event):
    meta = event.labour_event_meta
    return generic_publish_unpublish_view(
        request, vars, event,
        meta=event.labour_event_meta,
        template='labour_admin_startstop_view.jade',
        FormClass=StartStopForm,
    )


# TODO move under core
@require_http_methods(["GET", "HEAD", "POST"])
def generic_publish_unpublish_view(
    request,
    vars,
    event,
    meta,
    template,
    FormClass,
    save_success_message=_("Application period start and end times were saved."),
    end_time_clear_message=_(
        "The end of the application period was in the past and has now been cleared. "
        "If you have an ending date for the application period, please set it below."
    ),
    start_now_success_message=_("The application period was started."),
    already_public_message=_("The application period is already underway."),
    stop_now_success_message=_("The application period was ended."),
    not_public_message=_("The application period is not currently underway."),
):
    form = initialize_form(FormClass, request, instance=meta)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save':
            if form.is_valid():
                form.save()
                messages.success(request, save_success_message)
                return redirect(request.path)
            else:
                messages.error(request, _("Please check the form."))

        elif action == 'start-now':
            if not meta.is_public:
                if meta.publish():
                    messages.warning(request, end_time_clear_message)

                messages.success(request, start_now_success_message)
            else:
                messages.error(request, already_public_message)

            return redirect(request.path)

        elif action == 'stop-now':
            if meta.is_public:
                meta.unpublish()
                messages.success(request, stop_now_success_message)
            else:
                messages.error(request, not_public_message)

            return redirect(request.path)

        else:
            messages.error(request, _("Invalid request."))

    vars.update(
        meta=meta,
        form=form,
    )

    return render(request, template, vars)
