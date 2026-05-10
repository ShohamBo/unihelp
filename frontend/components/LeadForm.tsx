'use client'

import { useState } from 'react'
import { submitLead } from '@/lib/api'

interface Props {
  programSlug?: string
  institutionSlug?: string
  programName?: string
}

type Step = 'contact' | 'scores' | 'success'

export default function LeadForm({ programSlug, institutionSlug, programName }: Props) {
  const [step, setStep] = useState<Step>('contact')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    psychometric_score: '',
    consent_marketing: false,
  })

  function set(field: keyof typeof form, value: string | boolean) {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await submitLead({
        full_name: form.full_name,
        email: form.email,
        phone: form.phone,
        program_slug: programSlug,
        institution_slug: institutionSlug,
        psychometric_score: form.psychometric_score ? Number(form.psychometric_score) : undefined,
        consent_marketing: form.consent_marketing,
        source_page: window.location.pathname,
      })
      if (res.ok) {
        setStep('success')
      } else {
        setError('אירעה שגיאה. נסה שוב.')
      }
    } catch {
      setError('אירעה שגיאת רשת. נסה שוב.')
    } finally {
      setLoading(false)
    }
  }

  if (step === 'success') {
    return (
      <div className="text-center py-8">
        <div className="text-4xl mb-4">✅</div>
        <h3 className="text-xl font-bold text-gray-900 mb-2">תודה! קיבלנו את פנייתך</h3>
        <p className="text-gray-600 text-sm">נציג יצור איתך קשר בקרוב עם פרטים על {programName ?? 'התוכנית'}.</p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {programName && (
        <p className="text-sm text-gray-600 mb-1">
          קבל פרטים על <strong>{programName}</strong> ישירות מהמוסד
        </p>
      )}

      {/* Step 1: Contact */}
      {step === 'contact' && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">שם מלא</label>
            <input
              className="input"
              type="text"
              required
              placeholder="ישראל ישראלי"
              value={form.full_name}
              onChange={e => set('full_name', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">דוא"ל</label>
            <input
              className="input"
              type="email"
              required
              placeholder="israel@example.com"
              value={form.email}
              onChange={e => set('email', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">טלפון</label>
            <input
              className="input"
              type="tel"
              required
              placeholder="050-0000000"
              value={form.phone}
              onChange={e => set('phone', e.target.value)}
            />
          </div>
          <button
            type="button"
            className="btn-primary w-full"
            onClick={() => {
              if (!form.full_name || !form.email || !form.phone) {
                setError('יש למלא את כל השדות')
                return
              }
              setError('')
              setStep('scores')
            }}
          >
            המשך
          </button>
        </>
      )}

      {/* Step 2: Scores + consent */}
      {step === 'scores' && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              ציון פסיכומטרי (אופציונלי)
            </label>
            <input
              className="input"
              type="number"
              min={200}
              max={800}
              placeholder="למשל: 680"
              value={form.psychometric_score}
              onChange={e => set('psychometric_score', e.target.value)}
            />
          </div>
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              className="mt-1 rounded border-gray-300 text-brand-600"
              checked={form.consent_marketing}
              onChange={e => set('consent_marketing', e.target.checked)}
            />
            <span className="text-sm text-gray-600">
              אני מסכים/ה לקבל עדכונים ומידע על תוכניות לימוד מהמוסדות הרלוונטיים
            </span>
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-3">
            <button
              type="button"
              className="btn-outline flex-1"
              onClick={() => setStep('contact')}
            >
              חזרה
            </button>
            <button type="submit" className="btn-primary flex-1" disabled={loading}>
              {loading ? 'שולח...' : 'שלח פנייה'}
            </button>
          </div>
        </>
      )}

      {error && step === 'contact' && <p className="text-sm text-red-600">{error}</p>}

      <p className="text-xs text-gray-400 text-center">
        הפרטים שלך לא יועברו לצדדים שלישיים ללא הסכמתך
      </p>
    </form>
  )
}
