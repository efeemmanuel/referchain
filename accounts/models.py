from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    """
    Custom manager for the User model.
    We override the default manager because we are using email as the login
    field instead of username. Django requires us to define how users
    and superusers are created when we use a custom User model.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and returns a regular user with an email and password.
        normalize_email converts USER@GMAIL.COM to user@gmail.com for consistency.
        set_password hashes the password so it is never stored as plain text.
        """
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Creates and returns a superuser.
        A superuser has is_staff=True and is_superuser=True which gives
        full access to the Django admin panel at /admin.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    ... your docstring ...
    """

    class Role(models.TextChoices):
        HOSPITAL_ADMIN = 'hospital_admin', 'Hospital Admin'
        DOCTOR = 'doctor', 'Doctor'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name='custom_user_set'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='custom_user_set'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.email



# class User(AbstractBaseUser, PermissionsMixin):
#     """
#     Custom User model for ReferChain.

#     We extend AbstractBaseUser instead of the default Django User model
#     because we need to use email as the login field and add a role field.

#     AbstractBaseUser — gives us password hashing and authentication logic
#     without assuming anything about our fields. We define everything ourselves.

#     PermissionsMixin — adds Django's built-in permissions system.
#     Required for the admin panel and role based access control.

#     Two types of users exist in this system:
#     - hospital_admin: manages the hospital account, invites doctors
#     - doctor: creates patients and referrals
#     """

#     class Role(models.TextChoices):
#         """
#         TextChoices gives us a controlled list of valid role values.
#         Prevents random strings like 'Admin' or 'ADMIN' from being stored.
#         The format is: DB_VALUE = 'db_value', 'Human Readable Label'
#         """
#         HOSPITAL_ADMIN = 'hospital_admin', 'Hospital Admin'
#         DOCTOR = 'doctor', 'Doctor'

#     email = models.EmailField(
#         unique=True
#         # unique=True means no two users can share the same email.
#         # This is also our USERNAME_FIELD so it must be unique.
#     )
#     role = models.CharField(
#         max_length=20,
#         choices=Role.choices
#         # Stores either 'hospital_admin' or 'doctor'.
#         # This is how we control what a user can do after login.
#     )
#     is_active = models.BooleanField(
#         default=True
#         # If False, the user cannot log in.
#         # Lets us deactivate accounts without deleting them.
#     )
#     is_staff = models.BooleanField(
#         default=False
#         # If True, the user can access the Django admin panel at /admin.
#         # Only superusers and staff need this.
#     )
#     created_at = models.DateTimeField(
#         auto_now_add=True
#         # Automatically sets the timestamp when the record is first created.
#         # auto_now_add means it is set once and never changed.
#     )

#     # Tells Django to use email instead of username for authentication.
#     USERNAME_FIELD = 'email'

#     # No additional required fields beyond email and password.
#     REQUIRED_FIELDS = []

#     # Connects our custom UserManager so Django knows how to create users.
#     objects = UserManager()

#     def __str__(self):
#         # Controls what shows when you print a User object.
#         # e.g. print(user) → user@email.com
#         return self.email