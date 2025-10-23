# CDA TA Dashboard

A Canvas LMS Teaching Assistant Dashboard application designed to streamline grading workflow and monitor assignment status across courses.

## Features

- **Assignment Tracking**: Monitor assignment status with due dates and direct Canvas links
- **TA Grading Management**: Specialized dashboard for workload distribution across TA groups
- **Course Filtering**: Efficient workflow with course and assignment filtering
- **Real-time Integration**: Direct Canvas API integration for up-to-date information
- **Dual View System**: Assignment List + TA Grading Management interfaces

## Architecture

### Backend
- **FastAPI** (Python): Modern async web framework
- **canvasapi**: Official Canvas LMS Python library
- **Pydantic v2**: Data validation and settings management
- **Loguru**: Structured logging

### Frontend
- **React 19.1.1**: Modern UI library with concurrent features
- **Vite**: Fast, modern build tool
- **Tailwind CSS v4**: Utility-first CSS framework
- **Lucide React**: Consistent iconography

## Quick Start

### Prerequisites

- **Python 3.8.1+** (backend)
- **Node.js 16+** (frontend)
- **uv** package manager (recommended for Python)
- **Canvas LMS API Token** ([How to generate](SECURITY.md#generating-canvas-api-tokens))

### Backend Setup

```bash
cd backend-canvas-fastapi

# Install dependencies with uv
uv sync

# Create .env file from template
cp .env.example .env

# Edit .env with your Canvas credentials
# CANVAS_API_TOKEN=your-token-here
# CANVAS_BASE_URL=https://your-school.instructure.com
# CANVAS_COURSE_ID=your-course-id

# Run development server
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd canvas-react

# Install dependencies
npm install

# Create .env file from template
cp .env.example .env

# Edit .env with your Canvas and backend URLs
# VITE_CANVAS_API_URL=https://your-school.instructure.com
# VITE_CANVAS_API_KEY=your-canvas-api-token
# VITE_CANVAS_COURSE_ID=12345
# VITE_BACKEND_URL=http://localhost:8000

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Docker Deployment

Build and run the entire stack with Docker:

```bash
# Build Docker image
docker build -t cda-ta-dashboard:local .

# Run container
docker run -it --rm \
  -p 8000:8000 \
  -e CANVAS_API_TOKEN=your-token-here \
  -e CANVAS_BASE_URL=https://your-school.instructure.com \
  cda-ta-dashboard:local
```

Or use the convenience script:

```bash
./docker-build-and-run.sh
```

## Security

⚠️ **IMPORTANT**: This application handles sensitive student data and Canvas API credentials.

### Before Using

1. **Read [SECURITY.md](SECURITY.md)** for complete security guidelines
2. **Never commit** `.env` files or API tokens to version control
3. **Regenerate** Canvas API tokens before deploying to production
4. **Configure CORS** properly for production (not `*`)
5. **Install pre-commit hooks** to prevent accidental secret commits

### Quick Security Setup

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Verify .env files are gitignored
git status  # Should NOT show .env files
```

For detailed security practices, credential management, and deployment guidelines, see [SECURITY.md](SECURITY.md).

## Development

### Backend Development

```bash
cd backend-canvas-fastapi

# Run tests
uv run pytest

# Linting and formatting with Ruff
uv run ruff check .           # Lint code
uv run ruff check . --fix     # Lint and auto-fix issues
uv run ruff format .          # Format code

# Type checking
uv run mypy .

# Run with auto-reload
uv run python main.py
```

### Frontend Development

```bash
cd canvas-react

# Development server (with hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Linting
npm run lint
```

## Project Structure

```
cda-ta-dashboard/
├── backend-canvas-fastapi/     # FastAPI backend
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration management
│   ├── models.py               # Pydantic models
│   ├── dependencies.py         # FastAPI dependencies
│   ├── routers/                # API route modules
│   ├── services/               # Business logic
│   └── .env.example            # Environment template
├── canvas-react/               # React frontend
│   ├── src/
│   │   ├── App.jsx             # Main TA dashboard
│   │   └── TAGradingDashboard.jsx  # TA grading interface
│   ├── public/                 # Static assets
│   ├── .env.example            # Environment template
│   └── vite.config.js          # Vite configuration
├── Dockerfile                  # Multi-stage Docker build
├── docker-build-and-run.sh     # Docker convenience script
├── SECURITY.md                 # Security guidelines
├── AGENTS.md                   # Project documentation for Claude Code
└── README.md                   # This file
```

## API Endpoints

### Backend API (port 8000)

- `GET /api/health` - Health check
- `POST /api/validate-credentials` - Validate Canvas API credentials
- `POST /api/assignments` - Fetch assignments from courses
- `POST /api/assignment/{id}/details` - Get assignment details
- `POST /api/ta-groups/{course_id}` - Fetch TA groups
- `POST /api/ta-grading` - Get ungraded submissions with TA assignments

Full API documentation available at `http://localhost:8000/docs` (Swagger UI)

## Environment Variables

### Backend Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `CANVAS_API_TOKEN` | Canvas API access token | Yes | None |
| `CANVAS_BASE_URL` | Canvas instance URL | Yes | None |
| `CANVAS_COURSE_ID` | Default course ID | No | None |
| `PORT` | Server port | No | 8000 |
| `DEBUG` | Enable debug mode | No | True |
| `CORS_ORIGINS` | Allowed CORS origins | No | `["*"]` |

### Frontend Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `VITE_CANVAS_API_URL` | Canvas instance URL | Yes | None |
| `VITE_CANVAS_API_KEY` | Canvas API token | Yes | None |
| `VITE_CANVAS_COURSE_ID` | Course ID(s) | Yes | None |
| `VITE_BACKEND_URL` | Backend API URL | No | `http://localhost:8000` |

See `.env.example` files for complete configuration templates.

## Contributing

### Pre-commit Hooks

Install pre-commit hooks to ensure code quality and prevent security issues:

```bash
# Install pre-commit package
pip install pre-commit

# Install git hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### Code Style

- **Python**: Ruff (formatting + linting, replaces Black/isort/flake8)
- **JavaScript/React**: ESLint with React hooks rules
- **Commits**: Conventional commits preferred

## Data Privacy & Compliance

This application accesses student data from Canvas LMS. Ensure compliance with:

- **FERPA**: Family Educational Rights and Privacy Act
- **GDPR**: If serving EU students
- **Institutional Policies**: Your institution's data handling requirements

See [SECURITY.md](SECURITY.md) for detailed data privacy guidelines.

## Troubleshooting

### Common Issues

**Canvas API Token Invalid**
- Verify token hasn't expired in Canvas settings
- Check token has correct permissions
- Regenerate token if necessary

**CORS Errors**
- Ensure `CORS_ORIGINS` includes your frontend URL
- Check backend is running on correct port
- Verify API requests use correct backend URL

**Build Errors**
- Clear caches: `rm -rf node_modules/.vite`
- Reinstall dependencies: `npm install` or `uv sync`
- Check Node.js and Python versions match requirements

## Resources

- [Canvas API Documentation](https://canvas.instructure.com/doc/api/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Project Security Guidelines](SECURITY.md)

## License

[Add license information here]

## Support

For security issues, see [SECURITY.md](SECURITY.md) for responsible disclosure.

For bugs and features, please open a GitHub issue.

---

**Maintained by**: CDA TA Dashboard Team
**Last Updated**: 2025-10-10
