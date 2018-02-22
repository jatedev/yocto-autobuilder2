from buildbot.plugins import worker
from yoctoabb import config

workers = []

for w in config.workers:
    workers.append(worker.Worker(w, config.worker_password,
                                 max_builds=config.worker_max_builds,
                                 notify_on_missing=config.notify_on_missing))
