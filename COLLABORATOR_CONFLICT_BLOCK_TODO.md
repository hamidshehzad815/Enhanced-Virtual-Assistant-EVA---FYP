# Collaborator Conflict Blocking TODO

- [x] Review current add flow and identify collaborator insertion point.
- [x] Add shared DB helper to detect overlap for a user (owner tasks + accepted collaborations).
- [x] Use overlap helper for owner conflict check in add flow.
- [x] Add strict collaborator busy check before task insertion.
- [x] Return clear conflict response when collaborator is busy.
- [x] Keep task uncreated when collaborator conflict exists.
- [ ] Manual API validation in Postman (owner add with busy collaborator).
