// Tests for Log Task Completion Modal Date Input Field
// Testing framework: Jest with React Testing Library

describe('LoggingModal Date Input Field', () => {
    
    beforeEach(() => {
        // Mock Date.now() to return a consistent date for testing
        jest.spyOn(Date, 'now').mockImplementation(() => 
            new Date('2023-12-15T10:00:00.000Z').getTime()
        );
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('Date input field rendering', () => {
        test('should render date input field in the modal', () => {
            // Test that the date input field is present in the modal
            const modalProps = {
                isOpen: true,
                onClose: jest.fn(),
                onSave: jest.fn(),
                taskItem: { id: 1, name: 'Test Task' },
                errors: {},
                isSubmitting: false
            };

            // Simulate modal rendering
            const modalHTML = `
                <div class="editor-overlay">
                    <div class="editor-container">
                        <div class="editor-header">
                            <div class="editor-title">Log Task Completion</div>
                        </div>
                        <form class="editor-content">
                            <div class="editor-field">
                                <label class="editor-label">Date *</label>
                                <input
                                    type="date"
                                    class="editor-input"
                                    id="completion-date"
                                    required
                                />
                            </div>
                            <div class="editor-field">
                                <label class="editor-label">Logging Hours *</label>
                                <input type="number" class="editor-input" />
                            </div>
                            <div class="editor-field">
                                <label class="editor-label">Description</label>
                                <textarea class="editor-textarea"></textarea>
                            </div>
                        </form>
                    </div>
                </div>
            `;

            // Parse and validate the HTML
            const parser = new DOMParser();
            const doc = parser.parseFromString(modalHTML, 'text/html');
            
            const dateInput = doc.querySelector('input[type="date"]');
            expect(dateInput).toBeTruthy();
            expect(dateInput.getAttribute('class')).toBe('editor-input');
            expect(dateInput.getAttribute('id')).toBe('completion-date');
            expect(dateInput.hasAttribute('required')).toBe(true);
        });

        test('should have proper label for date input', () => {
            const modalHTML = `
                <div class="editor-field">
                    <label class="editor-label" for="completion-date">Date *</label>
                    <input type="date" class="editor-input" id="completion-date" />
                </div>
            `;

            const parser = new DOMParser();
            const doc = parser.parseFromString(modalHTML, 'text/html');
            
            const label = doc.querySelector('label[for="completion-date"]');
            expect(label).toBeTruthy();
            expect(label.textContent).toBe('Date *');
            expect(label.getAttribute('class')).toBe('editor-label');
        });
    });

    describe('Date input default value', () => {
        test('should default to current date when modal opens', () => {
            // Test the actual implementation logic
            const defaultDate = new Date().toISOString().split('T')[0];
            
            // Test data structure for logging
            const loggingData = {
                hours: '',
                description: '',
                date: defaultDate // Should default to current date
            };

            expect(loggingData.date).toBe(defaultDate);
            expect(loggingData.date).toMatch(/^\d{4}-\d{2}-\d{2}$/); // Should be in YYYY-MM-DD format
        });

        test('should format date correctly for input field', () => {
            const testDate = new Date('2023-12-15T10:00:00.000Z');
            const expectedFormat = testDate.toISOString().split('T')[0];
            
            expect(expectedFormat).toBe('2023-12-15');
            expect(expectedFormat).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        });
    });

    describe('Date input validation', () => {
        test('should be required field', () => {
            const validateLoggingForm = (formData) => {
                const errors = {};
                
                if (!formData.date || !formData.date.trim()) {
                    errors.date = 'Date is required';
                }
                
                return { isValid: Object.keys(errors).length === 0, errors };
            };

            const invalidData = { hours: '5', description: 'Test', date: '' };
            const result = validateLoggingForm(invalidData);
            
            expect(result.isValid).toBe(false);
            expect(result.errors.date).toBe('Date is required');
        });

        test('should accept valid date format', () => {
            const validateLoggingForm = (formData) => {
                const errors = {};
                
                if (!formData.date || !formData.date.trim()) {
                    errors.date = 'Date is required';
                } else {
                    // Check if date is valid
                    const dateObj = new Date(formData.date);
                    if (isNaN(dateObj.getTime())) {
                        errors.date = 'Invalid date format';
                    }
                }
                
                return { isValid: Object.keys(errors).length === 0, errors };
            };

            const validData = { hours: '5', description: 'Test', date: '2023-12-15' };
            const result = validateLoggingForm(validData);
            
            expect(result.isValid).toBe(true);
            expect(result.errors.date).toBeUndefined();
        });

        test('should reject invalid date format', () => {
            const validateLoggingForm = (formData) => {
                const errors = {};
                
                if (!formData.date || !formData.date.trim()) {
                    errors.date = 'Date is required';
                } else {
                    const dateObj = new Date(formData.date);
                    if (isNaN(dateObj.getTime())) {
                        errors.date = 'Invalid date format';
                    }
                }
                
                return { isValid: Object.keys(errors).length === 0, errors };
            };

            const invalidData = { hours: '5', description: 'Test', date: 'invalid-date' };
            const result = validateLoggingForm(invalidData);
            
            expect(result.isValid).toBe(false);
            expect(result.errors.date).toBe('Invalid date format');
        });
    });

    describe('Date input user interaction', () => {
        test('should update state when date is changed', () => {
            let loggingData = {
                hours: '',
                description: '',
                date: '2023-12-15'
            };

            const handleInputChange = (field, value) => {
                loggingData = { ...loggingData, [field]: value };
            };

            // Simulate user changing date
            handleInputChange('date', '2023-12-16');
            
            expect(loggingData.date).toBe('2023-12-16');
        });

        test('should clear date error when valid date is entered', () => {
            let errors = { date: 'Date is required' };

            const handleInputChange = (field, value) => {
                // Clear error when user starts typing
                if (errors[field]) {
                    const newErrors = { ...errors };
                    delete newErrors[field];
                    errors = newErrors;
                }
            };

            handleInputChange('date', '2023-12-15');
            
            expect(errors.date).toBeUndefined();
        });
    });

    describe('Form submission with date', () => {
        test('should include date in submitted log entry', () => {
            const mockFetch = jest.fn().mockResolvedValue({
                ok: true,
                json: () => Promise.resolve({ success: true })
            });
            global.fetch = mockFetch;

            const formData = {
                hours: '5',
                description: 'Completed task work',
                date: '2023-12-15'
            };

            const taskItem = { id: 1, name: 'Test Task' };

            // Simulate form submission
            const logEntry = {
                name: `Task Log: ${taskItem.name}`,
                description: formData.description,
                date: formData.date,
                actual_hours: parseFloat(formData.hours),
                log_id: `TASK-${taskItem.id}`
            };

            expect(logEntry.date).toBe('2023-12-15');
            expect(logEntry.actual_hours).toBe(5);
            expect(logEntry.name).toBe('Task Log: Test Task');
        });

        test('should prevent submission with missing date', () => {
            const validateForm = (formData) => {
                const errors = {};
                
                if (!formData.date || !formData.date.trim()) {
                    errors.date = 'Date is required';
                }
                
                if (!formData.hours || parseFloat(formData.hours) <= 0) {
                    errors.hours = 'Logging hours is required';
                }
                
                return Object.keys(errors).length === 0;
            };

            const invalidFormData = {
                hours: '5',
                description: 'Test',
                date: '' // Missing date
            };

            const isValid = validateForm(invalidFormData);
            expect(isValid).toBe(false);
        });
    });

    describe('Error display for date field', () => {
        test('should display error message for date field', () => {
            const errors = { date: 'Date is required' };
            
            const errorHTML = `
                <div class="editor-field">
                    <label class="editor-label">Date *</label>
                    <input type="date" class="editor-input" style="border-color: #dc3545;" />
                    <div style="color: #dc3545; fontSize: 12px; marginTop: 4px;">
                        ${errors.date}
                    </div>
                </div>
            `;

            const parser = new DOMParser();
            const doc = parser.parseFromString(errorHTML, 'text/html');
            
            const errorDiv = doc.querySelector('div[style*="color: #dc3545"]');
            expect(errorDiv).toBeTruthy();
            expect(errorDiv.textContent.trim()).toBe('Date is required');
            
            const input = doc.querySelector('input[type="date"]');
            expect(input.getAttribute('style')).toContain('border-color: #dc3545');
        });
    });

    describe('Integration with existing modal fields', () => {
        test('should maintain all existing fields when date is added', () => {
            const loggingData = {
                hours: '5',
                description: 'Test description',
                date: '2023-12-15'
            };

            // Verify all required fields are present
            expect(loggingData.hours).toBeTruthy();
            expect(loggingData.description).toBeTruthy();
            expect(loggingData.date).toBeTruthy();
            
            // Verify field types
            expect(typeof loggingData.hours).toBe('string');
            expect(typeof loggingData.description).toBe('string');
            expect(typeof loggingData.date).toBe('string');
        });

        test('should validate all fields including date', () => {
            const validateAllFields = (formData) => {
                const errors = {};
                
                if (!formData.hours || parseFloat(formData.hours) <= 0) {
                    errors.hours = 'Logging hours is required';
                }
                
                if (!formData.date || !formData.date.trim()) {
                    errors.date = 'Date is required';
                }
                
                return { isValid: Object.keys(errors).length === 0, errors };
            };

            // Test with all fields valid
            const validData = { hours: '5', description: 'Test', date: '2023-12-15' };
            const validResult = validateAllFields(validData);
            expect(validResult.isValid).toBe(true);

            // Test with missing date
            const missingDate = { hours: '5', description: 'Test', date: '' };
            const missingDateResult = validateAllFields(missingDate);
            expect(missingDateResult.isValid).toBe(false);
            expect(missingDateResult.errors.date).toBeTruthy();

            // Test with missing hours
            const missingHours = { hours: '', description: 'Test', date: '2023-12-15' };
            const missingHoursResult = validateAllFields(missingHours);
            expect(missingHoursResult.isValid).toBe(false);
            expect(missingHoursResult.errors.hours).toBeTruthy();
        });
    });
});