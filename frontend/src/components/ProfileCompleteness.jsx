export default function ProfileCompleteness({ profile, hasResume }) {
  if (!profile) return null

  const details = [
    ['department', profile.department, 'add your department'],
    ['batch', profile.batch, 'add your batch'],
    ['cgpa', profile.cgpa, 'add your CGPA'],
    ['arrears', profile.arrears, 'add your arrears'],
    ['resume', hasResume, 'upload a resume to finish'],
  ]
  const completeCount = details.filter(([, value]) => value !== null && value !== undefined && value !== '' && value !== false).length
  const percentage = Math.round((completeCount / details.length) * 100)
  const missing = details.find(([, value]) => value === null || value === undefined || value === '' || value === false)

  return <section className="profile-completeness" aria-label={`Profile ${percentage}% complete`}>
    <div className="profile-completeness-heading">
      <strong>{percentage === 100 ? 'Profile complete' : `Profile ${percentage}% done`}</strong>
      {missing && <span>{missing[2]}.</span>}
    </div>
    <div className="profile-progress-track" role="progressbar" aria-valuenow={percentage} aria-valuemin="0" aria-valuemax="100">
      <span style={{ width: `${percentage}%` }} />
    </div>
  </section>
}
