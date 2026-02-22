"""
============================================================
REPOSITORY  –  Data Access Layer
------------------------------------------------------------
Encapsula la **lógica de acceso a la base de datos**
(CRUD, queries personalizadas) utilizando los modelos ORM.
Sirve como frontera entre la lógica de negocio (service)
y la persistencia.

⚠️ Alcance:
- Opera exclusivamente con Session y models.
- No expone endpoints, no valida requests, no envía correos.
============================================================
"""
