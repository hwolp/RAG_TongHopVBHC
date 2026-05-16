# Backend Architecture Refactor Notes

## Target Shape

- `routers/`: request/response mapping only.
- `services/`: domain folders for business workflows.
- `repositories/`: SQLAlchemy query accessors.
- `contracts/`: provider/vector/retriever abstractions.
- `rag_engine/`: concrete RAG adapters and DTOs.
- `utils/`: shared errors, enum conversion, time, and file storage helpers.

## Service Folder Layout

- `services/admin/`: admin directory, config, maintenance, vector admin, user management.
- `services/auth/`: authentication and token helpers.
- `services/chat/`: chat sessions, prompt execution, chat context, chat DTOs.
- `services/documents/`: document lifecycle, folder tree, tags.
- `services/jobs/`: background job queue, dispatcher, handlers, runner, worker entrypoint.
- `services/policies/`: shared access policies.
- `services/rag/`: document processing and prompt building.
- `services/sharing/`: sharing and SQP approval workflows.
- Root `services/` now only keeps package metadata; service implementations live inside domain folders.

## Current Backend Flows

### Upload and Index

1. Router calls a compatibility facade in `document_service`.
2. `DocumentUploadService` validates file input and creates a `Document`.
3. `DocumentIndexCoordinator` creates an index job when the file type is supported.
4. `JobDispatcher` routes the background job to `IndexDocumentJobHandler`.
5. `DocumentProcessor` loads/OCRs/chunks the file.
6. `ChromaDBManager` stores prepared chunks in Chroma.

### Chat Answer

1. Router calls `chat_service.queue_ai_answer` or `chat_service.ask_ai`.
2. `ChatAnswerService` validates user scope and session state.
3. `chat_context_service` builds recent history and attachment context.
4. `ChromaDBManager` retrieves context through the vector-store adapter.
5. `PromptBuilder` builds the final RAG prompt.
6. `OllamaAI` invokes the configured LLM provider.

### Sharing

1. Router calls a compatibility facade in `share_service`.
2. `ShareService` applies manager/admin policy.
3. Shared core methods create or revoke `SharedDocument` records.
4. List operations use one presenter path for manager/admin share views.

## Compatibility Rules

- Existing HTTP routes and response shapes are preserved.
- Module-level service functions remain as facades for current routers and tests.
- Legacy endpoints are intentionally retained until frontend usage is audited.
- ChromaDB persisted files are not part of source refactor scope.

## Frontend Follow-up Backlog

- Split `frontend/src/api.ts` into typed domain clients.
- Extract repeated index badge/status UI into a reusable component.
- Split large pages such as `Chat.tsx` and `AdminUsers.tsx` into focused hooks and child components.
- Centralize API error rendering so pages do not each parse Axios errors differently.
