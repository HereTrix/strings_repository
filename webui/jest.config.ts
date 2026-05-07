/** @jest-config-loader ts-node */
/** @jest-config-loader-options {"transpileOnly": true} */

import { defineConfig } from 'jest';

export default defineConfig({
  verbose: true,
  testEnvironment: 'jsdom',
  // Add setupFilesAfterFramework: ['@testing-library/jest-dom'] when component tests are added
  transform: { '^.+\\.(ts|tsx|js|jsx)$': 'babel-jest' },
  moduleNameMapper: { '\\.(css|less|scss)$': '<rootDir>/__mocks__/fileMock.js' },
  testMatch: ['**/__tests__/**/*.test.(ts|tsx)'],
  collectCoverage: true,
  coverageReporters: ["json"],
});
