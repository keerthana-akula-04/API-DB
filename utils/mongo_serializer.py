from bson import ObjectId

def serialize_mongo(document):
    if isinstance(document, list):
        return [serialize_mongo(doc) for doc in document]

    if isinstance(document, dict):
        return {
            key: str(value) if isinstance(value, ObjectId) else value
            for key, value in document.items()
        }

    return document
