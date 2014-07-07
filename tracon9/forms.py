# encoding: utf-8

from django import forms

from crispy_forms.layout import Layout, Fieldset

from core.utils import horizontal_form_helper, indented_without_label
from labour.models import Signup

from .models import SignupExtra


class SignupExtraForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SignupExtraForm, self).__init__(*args, **kwargs)
        self.helper = horizontal_form_helper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'shift_type',
            'total_work',
            indented_without_label('construction'),
            indented_without_label('overseer'),

            Fieldset(u'Työtodistus',
                indented_without_label('want_certificate'),
                'certificate_delivery_address',
            ),
            Fieldset(u'Lisätiedot',
                'shirt_size',
                'special_diet',
                'special_diet_other',
                'lodging_needs',
                'prior_experience',
                'free_text',
            )
        )


    class Meta:
        model = SignupExtra
        fields = (
            'shift_type',
            'total_work',
            'construction',
            'overseer',
            'want_certificate',
            'certificate_delivery_address',
            'shirt_size',
            'special_diet',
            'special_diet_other',
            'lodging_needs',
            'prior_experience',
            'free_text',
        )

        widgets = dict(
            special_diet=forms.CheckboxSelectMultiple,
            lodging_needs=forms.CheckboxSelectMultiple,
        )



    def clean_certificate_delivery_address(self):
        want_certificate = self.cleaned_data['want_certificate']
        certificate_delivery_address = self.cleaned_data['certificate_delivery_address']

        if want_certificate and not certificate_delivery_address:
            raise forms.ValidationError(u'Koska olet valinnut haluavasi työtodistuksen, on '
                u'työtodistuksen toimitusosoite täytettävä.')

        return certificate_delivery_address


class OrganizerSignupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        job_categories = kwargs.pop('job_categories')
        super(SignupForm, self).__init__(*args, **kwargs)
        self.fields['job_categories'].queryset = job_categories

        self.helper = horizontal_form_helper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(u'Tehtävät',
                'job_categories'
            ),
        )

    class Meta:
        model = Signup
        fields = ()

        widgets = dict(
            job_categories=forms.CheckboxSelectMultiple,
        )


class OrganizerSignupExtraForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(OrganizerSignupExtraForm, self).__init__(*args, **kwargs)
        self.helper = horizontal_form_helper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(u'Lisätiedot',
                'shirt_size',
                'special_diet',
                'special_diet_other',
            )
        )


    class Meta:
        model = SignupExtra
        fields = (
            'shirt_size',
            'special_diet',
            'special_diet_other',
        )

        widgets = dict(
            special_diet=forms.CheckboxSelectMultiple,
        )

    @classmethod
    def get_excluded_field_defaults(cls):
        return dict(
            shift_type='kaikkikay',
            total_work='yli12h',
            construction=False,
            overseer=False,
            want_certificate=False,
            certificate_delivery_address=u'',
            lodging_needs=[],
            prior_experience=u'',
            free_text=u'Syötetty käyttäen coniitin ilmoittautumislomaketta',
        )
