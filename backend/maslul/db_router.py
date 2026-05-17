DATA_APPS = {"programs", "reviews"}


class MaslulRouter:
    def db_for_read(self, model, **hints):
        return "data" if model._meta.app_label in DATA_APPS else "default"

    def db_for_write(self, model, **hints):
        return "data" if model._meta.app_label in DATA_APPS else "default"

    def allow_relation(self, obj1, obj2, **hints):
        db1 = "data" if obj1._meta.app_label in DATA_APPS else "default"
        db2 = "data" if obj2._meta.app_label in DATA_APPS else "default"
        return db1 == db2

    def allow_migrate(self, db, app_label, **hints):
        if app_label in DATA_APPS:
            return db == "data"
        return db == "default"
