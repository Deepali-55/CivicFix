# CivicFix – Software Testing Documentation

## 1. Introduction
This document describes the testing activities performed on the CivicFix – Smart Public Complaint Management System.

## 2. Testing Objectives
- Verify citizen registration and login.
- Verify complaint submission and tracking.
- Verify AI-assisted complaint category suggestions.
- Verify administrator complaint management.
- Verify image upload validation.
- Check database storage and retrieval.

## 3. Test Cases

| Test ID | Test Scenario | Expected Result | Actual Result |
|---|---|---|---|
| TC01 | Citizen registration | Account should be created | Not yet verified |
| TC02 | Citizen login | User should log in successfully | Not yet verified |
| TC03 | Complaint submission | Complaint should be saved | Not yet verified |
| TC04 | AI category suggestion | Suggested category should appear | Tested |
| TC05 | Admin status update | Complaint status should update | Not yet verified |
| TC06 | Admin remark | Remark should be saved | Passed |
| TC07 | Citizen views remark | Remark should be visible | Passed |
| TC08 | Invalid PDF upload | Unsupported file should be rejected | Passed |
| TC09 | Complaint tracking | Complaint details should appear | Not yet verified |
| TC10 | Database persistence | Data should remain after restart | Not yet verified |

## 4. Testing Methods
- Manual functional testing
- Input validation testing
- Image upload validation testing
- Database testing
- Automated testing using Python unittest

## 5. Testing Status
Some manual tests have been completed successfully. Other test cases and the complete automated test suite require further verification.

## 6. Conclusion
Testing helps verify the functionality, reliability and correctness of CivicFix. Further testing is required before considering the application ready for production deployment.