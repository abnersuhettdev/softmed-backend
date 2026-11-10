# Backend Development Plan for Doctor Features

This plan outlines the incremental steps to implement the features described in `DOCTOR_BACKEND.md`.

## Phase 1: Core Queue Management and Status Tracking

1.  **Implement User Status and Queue Time Fields:**
    *   **Description:** Add `queue_status` (String, indexed, default 'waiting') and `queue_entry_time` (DateTime, nullable) fields to the `User` model in `app/models/user.py`. This will allow tracking of customer states within the queue.
    *   **Verification:** Ensure these fields are correctly added to the database schema via Alembic migrations.

2.  **Develop Queue Service Logic:**
    *   **Description:** Enhance `app/services/queue_service.py` to manage user queue status. Implement methods for:
        *   `add_to_queue(patient_id)`: Sets user status to 'waiting' and records `queue_entry_time`.
        *   `remove_from_queue(patient_id)`: Removes user from queue (e.g., sets status to 'completed', 'no_wait', or 'cancelled').
        *   `get_queue()`: Returns a list of patients currently in the 'waiting' state.
        *   `get_customers_in_service()`: Returns a list of patients with 'in_service' status.
        *   `get_completed_services_count()`: Returns the count of users with 'completed' status.
        *   `get_no_wait_services_count()`: Returns the count of users with 'no_wait' status.
        *   `get_next_patient()`: Retrieves the next patient from the 'waiting' queue.
        *   `update_patient_status(patient_id, new_status)`: Updates a patient's status.
    *   **Verification:** Unit tests for all new service methods.

3.  **Create Queue API Endpoints:**
    *   **Description:** Implement endpoints in `app/routers/queue.py` to interact with the `QueueService`:
        *   `POST /queue/add/{patient_id}`: Adds a patient to the queue.
        *   `DELETE /queue/remove/{patient_id}`: Removes a patient from the queue.
        *   `GET /queue`: Retrieves the list of waiting patients.
        *   `GET /queue/in_service`: Retrieves the list of patients currently in service.
        *   `GET /queue/completed_count`: Retrieves the count of completed services.
        *   `GET /queue/no_wait_count`: Retrieves the count of patients who did not wait.
        *   `POST /queue/call_next`: (Doctor-specific) Calls the next patient in line.
    *   **Verification:** API tests for all new endpoints.

## Phase 2: Admin and Doctor Specific Features

4.  **Implement Queue On/Off Toggle:**
    *   **Description:** Add a mechanism (e.g., a new model `QueueSettings` or a global configuration) to control whether the service queue is active. Create an admin-only endpoint (e.g., `PUT /admin/queue/toggle`) to turn the queue on/off.
    *   **Verification:** Test the toggle functionality and ensure it affects queue operations.

5.  **Display Customer Details in Attendance:**
    *   **Description:** Enhance the `GET /queue/in_service` endpoint to return detailed customer information, including the name of the professional assisting them. This will require joining `User` with `Appointment` or a similar model that links patients to doctors.
    *   **Verification:** Verify that the endpoint returns the correct data format.

6.  **Display Detailed Waiting Customer List:**
    *   **Description:** Ensure the `GET /queue` endpoint returns comprehensive details for waiting customers, including `name`, `queue_entry_time`, and an indicator for `online` or `offline` status (this might require integration with a presence system or a simple status field).
    *   **Verification:** Verify the detailed output of the waiting queue.

7.  **Doctor's Call Next Client Functionality:**
    *   **Description:** Implement the `POST /queue/call_next` endpoint. This endpoint should:
        *   Identify the next patient in the 'waiting' queue.
        *   Update the patient's status to 'in_service'.
        *   Associate the patient with the calling doctor.
        *   (Optional, based on `DOCTOR_BACKEND.md` point 8) Generate a new meet call link and return it.
    *   **Verification:** Test the flow of calling the next patient and updating their status.

## Phase 3: Reporting and Refinements

8.  **Implement Reporting Endpoints:**
    *   **Description:** Create endpoints for the counts mentioned in points 1-4 of `DOCTOR_BACKEND.md`:
        *   Total customers currently in query (in service).
        *   Total customers in queue waiting.
        *   Total services completed.
        *   Total customers who did not wait.
    *   **Verification:** Test reporting endpoints to ensure accurate counts.

9.  **Admin Panel Integration Considerations:**
    *   **Description:** Document how the queue on/off toggle (point 5) and potentially other queue management features will be exposed and controlled via an admin panel. This might involve creating specific admin roles and permissions.
    *   **Verification:** This is a documentation step, no code changes required at this stage.

10. **Refine and Test:**
    *   **Description:** Conduct thorough end-to-end testing of all queue-related features. Optimize database queries and API responses.
    *   **Verification:** Final QA and performance testing.

This plan will be executed incrementally, with each step building upon the previous ones.