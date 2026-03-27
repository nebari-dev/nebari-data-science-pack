{{/*
Expand the name of the chart.
*/}}
{{- define "nebari-data-science-pack.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "nebari-data-science-pack.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "nebari-data-science-pack.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "nebari-data-science-pack.labels" -}}
helm.sh/chart: {{ include "nebari-data-science-pack.chart" . }}
{{ include "nebari-data-science-pack.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Validate shared storage configuration consistency.
sharedStorage.enabled (controls PVC creation) and
jupyterhub.custom.shared-storage-enabled (controls spawner mounts) must match.
A mismatch causes either a missing PVC error on every spawn or a dormant PVC.
*/}}
{{- define "nebari-data-science-pack.validateSharedStorage" -}}
{{- $pvEnabled := .Values.sharedStorage.enabled -}}
{{- $spawnEnabled := index .Values.jupyterhub.custom "shared-storage-enabled" | default false -}}
{{- if and $pvEnabled (not $spawnEnabled) -}}
{{- fail "Configuration mismatch: sharedStorage.enabled=true but jupyterhub.custom.shared-storage-enabled=false. Set both to true or both to false." -}}
{{- end -}}
{{- if and $spawnEnabled (not $pvEnabled) -}}
{{- fail "Configuration mismatch: jupyterhub.custom.shared-storage-enabled=true but sharedStorage.enabled=false. Set both to true or both to false." -}}
{{- end -}}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "nebari-data-science-pack.selectorLabels" -}}
app.kubernetes.io/name: {{ include "nebari-data-science-pack.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
