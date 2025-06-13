require('@testing-library/jest-dom');

// Mock DOM Parser for tests
if (typeof window !== 'undefined') {
    global.DOMParser = window.DOMParser;
} else {
    global.DOMParser = require('jsdom').JSDOM.fromURL('http://localhost').window.DOMParser;
}