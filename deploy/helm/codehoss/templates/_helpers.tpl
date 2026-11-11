{{- define "codehoss.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "codehoss.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "codehoss.selector" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: server
{{- end -}}

{{- define "codehoss.image" -}}
{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}
{{- end -}}

{{- define "codehoss.secretName" -}}
{{ .Values.existingSecret | default (printf "%s-secret" (include "codehoss.fullname" .)) }}
{{- end -}}

{{- define "codehoss.ollamaUrl" -}}
{{- if .Values.ollama.enabled -}}
http://{{ include "codehoss.fullname" . }}-ollama:11434
{{- else -}}
{{ .Values.ai.ollamaUrl }}
{{- end -}}
{{- end -}}

{{/* A PersistentVolumeClaim; args: (dict "ctx" $ "name" "data" "spec" .Values.persistence.data "keep" true) */}}
{{- define "codehoss.pvc" -}}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ include "codehoss.fullname" .ctx }}-{{ .name }}
  labels:
    {{- include "codehoss.labels" .ctx | nindent 4 }}
  {{- if .keep }}
  annotations:
    # Learners' accounts and work outlive an uninstall; delete the claim to drop them.
    helm.sh/resource-policy: keep
  {{- end }}
spec:
  accessModes: [ReadWriteOnce]
  {{- with .spec.storageClass }}
  storageClassName: {{ . | quote }}
  {{- end }}
  resources:
    requests:
      storage: {{ .spec.size }}
{{- end -}}
