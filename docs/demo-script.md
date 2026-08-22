# Walkthrough Demo Script (5-7 Minutes)

This script demonstrates the end-to-end conversational certificate application process.

---

## 1. Introduction (1 Minute)
* **Goal**: Explain the problem and project concept.
* **Script**: "Welcome! Today, we're presenting a Multilingual Voice-First Revenue Services platform. Instead of forcing citizens to fill out complex forms, our AI-powered assistant helps them apply for certificates using natural, regional language conversations."

---

## 2. Dynamic Service Selection (1 Minute)
* **Action**: In the Web Portal interface, select **Income Certificate** from the dropdown chip in the Header.
* **Visual Check**: A toast notification appears saying *"Starting application for Income Certificate"*, and the chat initiates automatically.
* **Bot Reply**: *"Certainly! I will start your Income Certificate application. First, please tell me your full name."*

---

## 3. Conversational Form-Filling (2 Minutes)
* **Action**: Type `"Ramesh Kumar"` and send.
* **Bot Reply**: *"Which district do you reside in?"*
* **Action**: Type `"Nagpur"` and send.
* **Bot Reply**: *"Thank you. What is your annual family income in Rupees?"*
* **Action**: Type `"450000"` and send.
* **Bot Reply**: *"Do you consent to share your synthetic Aadhaar and personal details for validation? (Say 'Yes' or 'No')"*
* **Action**: Type `"Yes"` and send.

---

## 4. Document Verification & DLP Check (1.5 Minutes)
* **Action**: The portal guides you to upload documents. Upload mock documents.
* **OCR Output**: The backend mock OCR reads the files and compares values.
* **DLP Guard**: Try entering `"My Aadhaar is 1234-5678-9012"`. Notice that the Sovereignty Guard intercepts it, flags the PII, and updates the Sovereignty Log.

---

## 5. Mock Payment & Submission (1 Minute)
* **Action**: Enter OTP `"123456"`.
* **Visual Check**: Shows calculated fee (₹50). Click **Pay ₹50** using the mock UPI dialog.
* **Bot Reply**: *"Your Income Certificate application has been successfully submitted. Application ID: INC-2026-XXXX."*
* **Status Page**: Check the dashboard and verify that the status has changed to `Approved / Certificate Ready`.
