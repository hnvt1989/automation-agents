-- Create user_settings table for storing user-specific configuration
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    setting_key VARCHAR(255) NOT NULL,
    setting_value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(user_id, setting_key),
    
    -- Foreign key to users table (custom user table)
    CONSTRAINT fk_user_settings_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_settings_setting_key ON user_settings(setting_key);
CREATE INDEX IF NOT EXISTS idx_user_settings_user_key ON user_settings(user_id, setting_key);

-- Enable Row Level Security
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
-- Note: Since using custom auth, we'll need to adjust these policies based on your auth implementation
-- For now, creating basic policies that can be customized
CREATE POLICY "Users can view their own settings" ON user_settings
    FOR SELECT USING (true);  -- Adjust based on your auth implementation

CREATE POLICY "Users can insert their own settings" ON user_settings
    FOR INSERT WITH CHECK (true);  -- Adjust based on your auth implementation

CREATE POLICY "Users can update their own settings" ON user_settings
    FOR UPDATE USING (true);  -- Adjust based on your auth implementation

CREATE POLICY "Users can delete their own settings" ON user_settings
    FOR DELETE USING (true);  -- Adjust based on your auth implementation

-- Create function to automatically update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_user_settings_updated_at 
    BEFORE UPDATE ON user_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default settings for existing users (if any exist)
-- This will create empty calendar link settings for all existing users
INSERT INTO user_settings (user_id, setting_key, setting_value)
SELECT 
    u.id as user_id,
    'google_drive_calendar_secret_link' as setting_key,
    '' as setting_value
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM user_settings us 
    WHERE us.user_id = u.id 
    AND us.setting_key = 'google_drive_calendar_secret_link'
);

-- Add a comment to the table
COMMENT ON TABLE user_settings IS 'Stores user-specific configuration settings';
COMMENT ON COLUMN user_settings.user_id IS 'Reference to the user in users table';
COMMENT ON COLUMN user_settings.setting_key IS 'The configuration key (e.g., google_drive_calendar_secret_link)';
COMMENT ON COLUMN user_settings.setting_value IS 'The configuration value';