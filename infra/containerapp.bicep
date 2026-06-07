param location string
param containerAppsEnvironmentName string
param containerAppName string
param containerImage string
param registryServer string
param projectEndpoint string
param foundryAgent string
param foundryAgentVersion string
param azureTenant string
param m365Tenant string
param identityId string
param identityClientId string

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-a365-foundry'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-a365-foundry-agent'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvironmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      registries: [
        {
          server: registryServer
          identity: identityId
        }
      ]
      ingress: {
        external: true
        targetPort: 3978
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'agent-host'
          image: containerImage
          env: [
            {
              name: 'APP_ENVIRONMENT'
              value: 'production'
            }
            {
              name: 'PROJECT_ENDPOINT'
              value: projectEndpoint
            }
            {
              name: 'FOUNDRY_AGENT'
              value: foundryAgent
            }
            {
              name: 'FOUNDRY_AGENT_VERSION'
              value: foundryAgentVersion
            }
            {
              name: 'AZURE_TENANT'
              value: azureTenant
            }
            {
              name: 'M365_TENANT'
              value: m365Tenant
            }
            {
              name: 'BOT_ID'
              value: identityClientId
            }
            {
              name: 'REQUIRE_BOT_AUTH'
              value: 'true'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: identityClientId
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
