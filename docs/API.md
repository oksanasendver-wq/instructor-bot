# API Documentation

## Instructor API (12 endpoints)

### Auth
- POST /api/instructor/auth/telegram
- POST /api/instructor/auth/request-contact

### Bookings
- GET /api/instructor/bookings/me/today
- POST /api/instructor/bookings/{id}/arrived
- POST /api/instructor/bookings/{id}/no-show
- POST /api/instructor/bookings/{id}/finish

### Reports
- POST /api/instructor/reports
- PATCH /api/instructor/reports/{id}

### Clients
- GET /api/instructor/clients/{id}/profile
- GET /api/instructor/clients/{id}/history

### Catalogs
- GET /api/instructor/catalogs/exercises
- GET /api/instructor/catalogs/skills

## Admin API (18 endpoints)

### Auth
- POST /admin/auth/login

### Bookings
- GET /admin/bookings
- POST /admin/bookings
- PATCH /admin/bookings/{id}
- DELETE /admin/bookings/{id}

### Instructors
- GET /admin/instructors
- POST /admin/instructors
- PATCH /admin/instructors/{id}
- DELETE /admin/instructors/{id}

### Clients
- GET /admin/clients
- POST /admin/clients
- PATCH /admin/clients/{id}
- DELETE /admin/clients/{id}

### AI Drafts
- POST /admin/clients/{id}/ai-draft
- GET /admin/clients/{id}/ai-drafts

### Attention Flags
- GET /admin/attention-flags
- GET /admin/clients/{id}/attention-flags
- POST /admin/attention-flags/{id}/close
