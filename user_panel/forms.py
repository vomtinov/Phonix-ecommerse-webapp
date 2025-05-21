from django import forms
from authentication.models import CustomUser,Address

class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['profile_image']

class UserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'profile_image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make profile image optional
        self.fields['profile_image'].required = False

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['name', 'city', 'landmark', 'district', 'state', 'pincode', 'phone', 'alternative_phone']