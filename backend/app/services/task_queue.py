import time
import queue
import logging
import threading
from typing import Dict, Any, Callable
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# Simulated Redis Context Vault: thread-safe dictionary for sub-millisecond hot cache operations
class RedisContextVault:
    _cache: Dict[str, str] = {}
    _lock = threading.Lock()

    @classmethod
    def set(cls, key: str, value: Any, expire_seconds: int = 3600):
        with cls._lock:
            cls._cache[key] = json_str = str(value)
            logger.debug(f"[Redis Vault] SET {key} = {json_str[:60]}... (expires {expire_seconds}s)")

    @classmethod
    def get(cls, key: str) -> str:
        with cls._lock:
            val = cls._cache.get(key)
            logger.debug(f"[Redis Vault] GET {key} -> {'Found' if val else 'Miss'}")
            return val

    @classmethod
    def delete(cls, key: str):
        with cls._lock:
            if key in cls._cache:
                del cls._cache[key]
                logger.debug(f"[Redis Vault] DEL {key}")

# Simulated Celery Async Task Queue
class CeleryTaskQueue:
    _queue = queue.Queue()
    _worker_thread = None
    _tasks: Dict[str, Dict[str, Any]] = {} # Track async task statuses
    _lock = threading.Lock()

    @classmethod
    def start_worker(cls):
        with cls._lock:
            if cls._worker_thread is None:
                cls._worker_thread = threading.Thread(target=cls._worker_loop, daemon=True)
                cls._worker_thread.start()
                logger.info("[Celery Worker] Async task worker thread started.")

    @classmethod
    def delay(cls, task_name: str, task_id: str, func: Callable, *args, **kwargs):
        """
        Equivalent to Celery's task.delay() or apply_async()
        """
        cls.start_worker()
        with cls._lock:
            cls._tasks[task_id] = {
                "task_name": task_name,
                "status": "PENDING",
                "result": None,
                "error": None
            }
        cls._queue.put((task_id, func, args, kwargs))
        logger.info(f"[Celery Queue] Enqueued task {task_name} (ID: {task_id})")
        return task_id

    @classmethod
    def get_task_status(cls, task_id: str) -> Dict[str, Any]:
        with cls._lock:
            return cls._tasks.get(task_id, {"status": "UNKNOWN"})

    @classmethod
    def _worker_loop(cls):
        while True:
            try:
                task_id, func, args, kwargs = cls._queue.get()
                logger.info(f"[Celery Worker] Executing task ID: {task_id}")
                with cls._lock:
                    if task_id in cls._tasks:
                        cls._tasks[task_id]["status"] = "STARTED"

                # Run task function
                try:
                    result = func(*args, **kwargs)
                    with cls._lock:
                        if task_id in cls._tasks:
                            cls._tasks[task_id]["status"] = "SUCCESS"
                            cls._tasks[task_id]["result"] = result
                    logger.info(f"[Celery Worker] Task ID: {task_id} completed successfully.")
                except Exception as e:
                    logger.error(f"[Celery Worker] Task ID: {task_id} failed: {e}")
                    with cls._lock:
                        if task_id in cls._tasks:
                            cls._tasks[task_id]["status"] = "FAILURE"
                            cls._tasks[task_id]["error"] = str(e)
                finally:
                    cls._queue.task_done()
            except Exception as e:
                logger.error(f"[Celery Worker] Exception in loop: {e}")
                time.sleep(1)

# Helper function to simulate OCR processing in the background (used by our document verification)
def simulate_document_ocr_task(document_id: int):
    logger.info(f"[Celery OCR Task] Started document analysis for doc_id: {document_id}")
    time.sleep(2)  # Simulate document reading delay
    db: Session = SessionLocal()
    try:
        from backend.app.models.models import Document, DocumentExtraction, Application
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            # Generate OCR results
            # Mock details matching our diagram for NCL: DOB mismatch if name matches
            extracted = {}
            confidence = 0.95
            status = "VALIDATED"
            error = None

            if doc.doc_type == "identity_proof": # Aadhaar
                extracted = {"full_name": "Vikram Patil", "dob": "12-05-2002", "document_name": "Aadhaar Card"}
            elif doc.doc_type == "caste_proof":
                # Let's mock a DOB mismatch in caste proof or school certificate (e.g. 12-05-2003)
                extracted = {"full_name": "Vikram Patil", "dob": "12-05-2003", "document_name": "Caste Certificate"}
            elif doc.doc_type == "income_proof":
                extracted = {"annual_income": 450000.0, "employer": "Rural Agri Farming", "document_name": "Form 16"}
            elif doc.doc_type == "address_proof":
                extracted = {"address": "Shanti Nagar, Nagpur", "document_name": "Utility Bill"}

            # Save extraction
            extract = db.query(DocumentExtraction).filter(DocumentExtraction.document_id == document_id).first()
            if not extract:
                extract = DocumentExtraction(document_id=document_id)
                db.add(extract)
            extract.extracted_data = extracted
            extract.confidence_score = confidence
            extract.status = status
            extract.error_message = error

            doc.status = "VALIDATED"
            doc.verification_result = "Simulated LayoutLMv3 Verification Complete"
            db.commit()

            # Trigger state machine check
            app = db.query(Application).filter(Application.id == doc.application_id).first()
            if app and app.states:
                state_data = dict(app.states.state_data)
                if "documents_uploaded" not in state_data:
                    state_data["documents_uploaded"] = {}
                state_data["documents_uploaded"][doc.doc_type] = "VALIDATED"
                
                if "ocr_results" not in state_data:
                    state_data["ocr_results"] = {}
                state_data["ocr_results"][doc.doc_type] = extracted
                
                app.states.state_data = state_data
                db.commit()

                from backend.app.services.state_machine import StateMachineOrchestrator
                StateMachineOrchestrator.process_state_transition(db, app.states, app, {}, app.channel)
                
            logger.info(f"[Celery OCR Task] Document {document_id} validation complete.")
    except Exception as e:
        logger.error(f"[Celery OCR Task] Error: {e}")
        db.rollback()
    finally:
        db.close()

# Helper function to simulate Payment reconciliation in background
def simulate_payment_reconciliation_task(payment_id: int):
    logger.info(f"[Celery Payment Task] Reconciling payment_id: {payment_id}")
    time.sleep(1) # Simulate gateway latency
    db: Session = SessionLocal()
    try:
        from backend.app.models.models import Payment, Application
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if payment:
            payment.status = "SUCCESS"
            db.commit()

            # Update app state
            app = db.query(Application).filter(Application.id == payment.application_id).first()
            if app and app.states:
                state_data = dict(app.states.state_data)
                state_data["payment_status"] = "SUCCESS"
                app.states.state_data = state_data
                db.commit()

                from backend.app.services.state_machine import StateMachineOrchestrator
                StateMachineOrchestrator.process_state_transition(db, app.states, app, {}, app.channel)
            logger.info(f"[Celery Payment Task] Payment {payment_id} reconciled successfully.")
    except Exception as e:
        logger.error(f"[Celery Payment Task] Error: {e}")
        db.rollback()
    finally:
        db.close()
