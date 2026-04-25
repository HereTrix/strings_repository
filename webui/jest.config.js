module.exports = {
  testEnvironment: 'jsdom',
  // Add setupFilesAfterFramework: ['@testing-library/jest-dom'] when component tests are added
  transform: { '^.+\\.(ts|tsx|js|jsx)$': 'babel-jest' },
  moduleNameMapper: { '\\.(css|less|scss)$': '<rootDir>/__mocks__/fileMock.js' },
  testMatch: ['**/__tests__/**/*.test.(ts|tsx)'],
}
