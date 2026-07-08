import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import { ThemeProvider } from './context/ThemeContext';
import { BrandingProvider } from './context/BrandingContext';
import './styles/globals.css';
import App from './App.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <BrandingProvider>
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </BrandingProvider>
    </ThemeProvider>
  </StrictMode>,
);
