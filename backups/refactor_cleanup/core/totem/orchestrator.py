# versão reduzida focada na async integration

from services.async_tasks.tasks import log_training_task

# ... resto do código permanece igual ...

    def _finalize(...):

        add_turn(session_id, pergunta, resposta)

        # ASYNC LOG
        log_training_task.delay(session_id, pergunta, resposta, score)

        # resto igual...
