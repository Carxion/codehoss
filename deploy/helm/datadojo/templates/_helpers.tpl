{{- define "datadojo.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "datadojo.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "datadojo.selector" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: server
{{- end -}}

{{- define "datadojo.image" -}}
{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}
{{- end -}}

{{- define "datadojo.secretName" -}}
{{ .Values.existingSecret | default (printf "%s-secret" (include "datadojo.fullname" .)) }}
{{- end -}}

{{- define "datadojo.ollamaUrl" -}}
{{- if .Values.ollama.enabled -}}
http://{{ include "datadojo.fullname" . }}-ollama:11434
{{- else -}}
{{ .Values.ai.ollamaUrl }}
{{- end -}}
{{- end -}}

{{/* A PersistentVolumeClaim; args: (dict "ctx" $ "name" "data" "spec" .Values.persistence.data "keep" true) */}}
{{- define "datadojo.pvc" -}}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ include "datadojo.fullname" .ctx }}-{{ .name }}
  labels:
    {{- include "datadojo.labels" .ctx | nindent 4 }}
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
