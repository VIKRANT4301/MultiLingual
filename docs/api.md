# API Endpoint Documentation

## 1. Services
- **GET `/api/v1/applications/services/list`**
  - **Description**: Returns all seeded government services.
  - **Response**: Array of service definitions.
  
- **GET `/api/v1/applications/services/{service_id}`**
  - **Description**: Returns configurations for a specific service.

---

## 2. Conversation
- **POST `/api/v1/conversation/message`**
  - **Description**: Sends a message to the conversational state machine.
  - **Payload**:
    ```json
    {
      "session_id": "session-12345",
      "text": "I want to apply for Income Certificate",
      "channel": "Web",
      "language": "en"
    }
    ```
  - **Response**: Extracted entities, bot reply text, current state, and validation fields.

---

## 3. Applications
- **GET `/api/v1/applications/`**
  - **Description**: Lists all submitted applications.

- **GET `/api/v1/applications/{application_id}`**
  - **Description**: Retrieves details and status of a specific application.

---

## 4. Dashboard
- **GET `/api/v1/dashboard/metrics`**
  - **Description**: Returns aggregate metrics (Total Applications, Completed, Pending, average processing time, etc.).

- **GET `/api/v1/dashboard/escalations`**
  - **Description**: Returns the human-escalation queue.

- **GET `/api/v1/dashboard/audits`**
  - **Description**: Returns the Sovereignty Guard audit log.
