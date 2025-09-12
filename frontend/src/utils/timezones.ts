// Utility for timezone dropdown options
export const timezoneOptions = Intl.supportedValuesOf("timeZone").map((tz) => ({
    label: tz,
    value: tz,
}))
