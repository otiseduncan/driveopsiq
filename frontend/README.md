# DriveOps-IQ Frontend

A React + TypeScript + Vite frontend for the DriveOps-IQ platform.

## Getting Started

### Prerequisites

- Node.js **22 or higher** (required — this project uses Vite 7 which requires Node 20+)
- npm 10+

### Installation

1. Clone the repository
2. Navigate to the frontend directory
3. Install dependencies:

```bash
npm install
# or
yarn install
# or
pnpm install
```

### Development

Start the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

The application will be available at `http://localhost:3000`

### Building for Production

```bash
npm run build
# or
yarn build
# or
pnpm build
```

### Preview Production Build

```bash
npm run preview
# or
yarn preview
# or
pnpm preview
```

## Project Structure

```
src/
├── components/     # Reusable UI components
├── hooks/          # Custom React hooks
├── pages/          # Page components
├── services/       # API services and external integrations
├── context/        # React context providers
└── main.tsx        # Application entry point
```

## Technologies Used

- **React 18** - Frontend framework
- **TypeScript** - Type safety and better developer experience
- **Vite** - Fast build tool and development server
- **ESLint** - Code linting and formatting

## License

This project is part of the SyferStack application.
