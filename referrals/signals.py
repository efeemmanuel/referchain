from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.conf import settings

from referrals.models import Referral


@receiver(post_save, sender=Referral)
def send_referral_notification(sender, instance, created, **kwargs):
    """
    Fires automatically every time a Referral record is saved.

    Two notifications:
    1. On creation — email to receiving hospital with patient summary
       including recent medical records
    2. On acceptance — email to patient with their code and QR code attached
    """
    referral = instance
    receiving_hospital = referral.receiving_hospital
    referring_hospital = referral.referring_hospital
    patient = referral.patient
    doctor = referral.referring_doctor

    # ── Notification 1 — new referral created ────────────────────────────────
    if created:
        receiving_email = receiving_hospital.user.email

        subject = f'New Patient Referral — {patient.name} [{referral.urgency_level.upper()}]'

        # Build medical records summary to include in email
        # Receiving hospital gets a full picture of the patient's history
        recent_records = patient.medical_records.all()[:10]
        if recent_records:
            records_summary = '\n--- MEDICAL RECORDS ---\n'
            for rec in recent_records:
                records_summary += f"""
Type:     {rec.get_record_type_display()}
Title:    {rec.title}
Details:  {rec.content}
Added by: {rec.created_by.name if rec.created_by else 'Hospital Admin'}
Date:     {rec.created_at.strftime('%d %b %Y')}
{'─' * 40}
"""
        else:
            records_summary = '\n--- MEDICAL RECORDS ---\nNo records added yet.\n'

        message = f"""
Dear {receiving_hospital.name},

You have received a new patient referral from {referring_hospital.name}.

--- PATIENT DETAILS ---
Name:         {patient.name}
Phone:        {patient.phone}
Email:        {patient.email or 'Not provided'}
Address:      {patient.address or 'Not provided'}

--- REFERRAL DETAILS ---
Referred by:  Dr. {doctor.name} ({doctor.specialty})
Urgency:      {referral.urgency_level.upper()}
Symptoms:     {referral.symptoms}

--- TEST ATTACHMENTS ---
{', '.join(referral.test_attachments) if referral.test_attachments else 'None'}
{records_summary}
Please log in to ReferChain to accept or reject this referral.

ReferChain Team
        """

        try:
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[receiving_email],
            )
            email.send(fail_silently=False)
        except Exception as e:
            print(f'Failed to send referral notification to hospital: {e}')

    # ── Notification 2 — referral accepted, notify patient ───────────────────
    if not created and referral.status == Referral.Status.ACCEPTED:
        _notify_patient_on_acceptance(referral)


def _notify_patient_on_acceptance(referral):
    """
    Sends the patient an email with:
    - Their referral code clearly displayed
    - QR code image attached for tech savvy patients
    - Clear instructions on what to do next

    Only sends if the patient has an email address.
    For patients without email — doctor gives them the code verbally
    or writes it down. SMS/WhatsApp can be added here later.
    """
    patient = referral.patient

    if not patient.email:
        # Patient has no email — nothing to send
        # In future this is where SMS/WhatsApp would go
        print(f'Patient {patient.name} has no email — skipping patient notification')
        return

    subject = f'Your Referral to {referral.receiving_hospital.name} has been Accepted'

    message = f"""
Dear {patient.name},

Good news. Your referral to {referral.receiving_hospital.name} has been accepted.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR REFERRAL CODE: {referral.unique_code}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Keep this code safe. You will need it when you arrive at {referral.receiving_hospital.name}.

--- WHAT TO DO NEXT ---
1. Visit {referral.receiving_hospital.name} at your earliest convenience

2. At the reception desk give them your code:
   {referral.unique_code}

3. If you have a smartphone you can also show the QR code
   attached to this email — the receptionist can scan it directly

--- REFERRAL SUMMARY ---
Referred by:    Dr. {referral.referring_doctor.name}
From:           {referral.referring_hospital.name}
To:             {referral.receiving_hospital.name}
Urgency:        {referral.urgency_level.upper()}

If you have any questions please contact {referral.referring_hospital.name} directly.

ReferChain — Nigeria's Digital Referral Network
    """

    try:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[patient.email],
        )

        # Attach QR code image if it exists
        if referral.qr_code:
            try:
                import os
                qr_path = os.path.join(
                    settings.MEDIA_ROOT,
                    str(referral.qr_code)
                )
                if os.path.exists(qr_path):
                    with open(qr_path, 'rb') as qr_file:
                        email.attach(
                            filename=f'referral_qr_{referral.unique_code}.png',
                            content=qr_file.read(),
                            mimetype='image/png'
                        )
            except Exception as e:
                # QR attachment failed — still send email without it
                print(f'Could not attach QR code: {e}')

        email.send(fail_silently=False)
        print(f'Patient notification sent to {patient.email}')

    except Exception as e:
        print(f'Failed to send patient notification: {e}')