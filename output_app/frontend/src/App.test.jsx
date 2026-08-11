import { render, screen } from '@testing-library/react';
import App from './App';

test('renders Food Order Dashboard title', () => {
  render(<App />);
  const titleElement = screen.getByText(/Food Order Dashboard/i);
  expect(titleElement).toBeInTheDocument();
});
