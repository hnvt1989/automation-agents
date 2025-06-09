import { useState, useCallback } from 'react'
import type { WorkspaceItem } from '@/types'

interface UseModalFormOptions {
  onSubmit: (data: any) => Promise<void>
  validate: (data: any) => Record<string, string>
}

export function useModalForm<T extends Record<string, any>>(
  initialData: T,
  options: UseModalFormOptions
) {
  const [formData, setFormData] = useState<T>(initialData)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDirty, setIsDirty] = useState(false)

  const handleChange = useCallback((
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    setIsDirty(true)
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }, [errors])

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    
    const validationErrors = options.validate(formData)
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setIsSubmitting(true)
    
    try {
      await options.onSubmit(formData)
      setIsDirty(false)
    } catch (error) {
      console.error('Form submission error:', error)
      setErrors({ submit: error.message || 'Failed to save. Please try again.' })
    } finally {
      setIsSubmitting(false)
    }
  }, [formData, options])

  const reset = useCallback((newData?: T) => {
    setFormData(newData || initialData)
    setErrors({})
    setIsDirty(false)
  }, [initialData])

  const updateField = useCallback((name: keyof T, value: any) => {
    setFormData(prev => ({ ...prev, [name]: value }))
    setIsDirty(true)
  }, [])

  return {
    formData,
    errors,
    isSubmitting,
    isDirty,
    handleChange,
    handleSubmit,
    reset,
    updateField,
    setErrors
  }
}