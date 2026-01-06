/**
 * This is a template that's compiled down to a definition of the
 * infrastructural resources required for running your application.
 *
 * For more information on the JSONNET language, see:
 * https://jsonnet.org/learning/getting_started.html
 */

// This file is generated once at template creation time and unlikely to change
// from that point forward.
local config = import '../skiff.json';
local util = import './util.libsonnet';

function(flaskApiImage, cause, sha, env='prod', branch='', repo='', buildId='', safetyWorkerImage, fastApiImage)
    // All Skiff applications get a *.allen.ai URL in addition to *.apps.allenai.org.
    // This domain is attached to a separate Ingress, as to support authentication
    // via either canonical domain.
    local allenAIHosts = util.getHosts(env, config, '.allen.ai');

    // In production you run should run two or more replicas of your
    // application, so that if one instance goes down or is busy (e.g., during
    // a deployment), users can still use the remaining replicas of your
    // application.
    //
    // However, if you use GPUs, which are expensive, consider setting the prod
    // replica count to 1 as a trade-off between availability and costs.
    //
    // In all other environments (e.g., adhocs) we run a single instance to
    // save money.
    local numReplicas = if env == 'prod' then config.replicas.prod else 1;

    // Each app gets it's own namespace.
    local namespaceName = config.appName;

    // Since we deploy resources for different environments in the same namespace,
    // we need to give things a fully qualified name that includes the environment
    // as to avoid unintentional collision / redefinition.
    local fullyQualifiedName = config.appName + '-' + env;

    // Every resource is tagged with the same set of labels. These labels serve the
    // following purposes:
    //  - They make it easier to query the resources, i.e.
    //      kubectl get pod -l app=my-app,env=staging
    //  - The service definition uses them to find the pods it directs traffic to.
    local namespaceLabels = {
        app: config.appName,
        contact: config.contact,
        team: config.team
    };

    local labels = namespaceLabels + {
        env: env
    };

    local selectorLabels = {
        app: config.appName,
        env: env
    };

    // By default multiple instances of your application could get scheduled
    // to the same node. This means if that node goes down your application
    // does too. We use the label below to avoid that.
    local antiAffinityLabels = {
        onlyOneOfPerNode: config.appName + '-' + env
    };
    local podLabels = labels + antiAffinityLabels;

    // Annotations carry additional information about your deployment that
    // we use for auditing, debugging and administrative purposes
    local annotations = {
        "apps.allenai.org/sha": sha,
        "apps.allenai.org/branch": branch,
        "apps.allenai.org/repo": repo,
        "apps.allenai.org/build": buildId
    };

    // Running on a GPU requires a special limit on the container, and a
    // specific nodeSelector.
    local gpuInConfig = std.count(std.objectFields(config), "gpu") > 0;

    // determine number of gpus
    local gpuLimits = if gpuInConfig then
        if config.gpu == "k80x2" || config.gpu == "a100-40gbx2" then
            { 'nvidia.com/gpu': 2 }
        else if config.gpu == "t4x4" then
            { 'nvidia.com/gpu': 4 }
        else
            { 'nvidia.com/gpu': 1 }
    else {};

    local nodeSelector = if gpuInConfig then
        if config.gpu == "k80" || config.gpu == "k80x2" then
            { 'cloud.google.com/gke-accelerator': 'nvidia-tesla-k80' }
        else if config.gpu == "p100" then
            { 'cloud.google.com/gke-accelerator': 'nvidia-tesla-p100' }
        else if config.gpu == "t4x4" then
            { 'cloud.google.com/gke-accelerator': 'nvidia-tesla-t4' }
        else if config.gpu == "a100-40gb" || config.gpu == "a100-40gbx2" then
            { 'cloud.google.com/gke-accelerator': 'nvidia-tesla-a100' }
        else
            error "invalid GPU specification; expected 'k80', 'k80x2', 'p100', 't4x4', 'a100-40gb', or 'a100-40gbx2' but got: " + config.gpu
    else
         { };

    // The port the API (Python Flask application) is bound to.
    local apiPort = 8000;

    // This is used to verify that the API is functional.
    local apiHealthCheck = {
        port: apiPort,
        scheme: 'HTTP'
    };

    local namespace = {
        apiVersion: 'v1',
        kind: 'Namespace',
        metadata: {
            name: namespaceName,
            labels: namespaceLabels
        }
    };


    local flaskDeployment = {
        apiVersion: 'apps/v1',
        kind: 'Deployment',
        metadata: {
            labels: labels,
            name: fullyQualifiedName,
            namespace: namespaceName,
            annotations: annotations + {
                'kubernetes.io/change-cause': cause
            }
        },
        spec: {
            progressDeadlineSeconds: 3600, // 30 minutes, A100s are slow to scale up.
            strategy: {
                type: 'RollingUpdate',
                rollingUpdate: {
                    maxSurge: numReplicas // This makes deployments faster.
                }
            },
            revisionHistoryLimit: 3,
            replicas: numReplicas,
            selector: {
                matchLabels: selectorLabels
            },
            template: {
                metadata: {
                    name: fullyQualifiedName,
                    namespace: namespaceName,
                    labels: podLabels,
                    annotations: annotations
                },
                spec: {
                    # This block tells the cluster that we'd like to make sure
                    # each instance of your application is on a different node. This
                    # way if a node goes down, your application doesn't:
                    # See: https://kubernetes.io/docs/concepts/configuration/assign-pod-node/#node-isolation-restriction
                    affinity: {
                        podAntiAffinity: {
                            requiredDuringSchedulingIgnoredDuringExecution: [
                                {
                                   labelSelector: {
                                        matchExpressions: [
                                            {
                                                    key: labelName,
                                                    operator: 'In',
                                                    values: [ antiAffinityLabels[labelName], ],
                                            } for labelName in std.objectFields(antiAffinityLabels)
                                       ],
                                    },
                                    topologyKey: 'kubernetes.io/hostname'
                                },
                            ]
                        },
                    },
                    nodeSelector: nodeSelector,
                    volumes: [
                        {
                            name: 'cfg',
                            secret: {
                                secretName: 'cfg'
                            }
                        },
                        {
                            name: 'modal',
                            secret: {
                                secretName: 'modal'
                            }
                        }
                    ],
                    containers: [
                        {
                            name: fullyQualifiedName + '-api',
                            image: flaskApiImage,
                            env: [
                                {
                                    name: 'SHA',
                                    value: sha
                                },
                                {
                                    name: 'GOOGLE_APPLICATION_CREDENTIALS',
                                    value: '/secret/cfg/service_account.json'
                                },
                                {
                                    name: 'MODAL_CONFIG_PATH',
                                    value: '/secret/.modal.toml'
                                }
                            ],
                            # The "probes" below allow Kubernetes to determine
                            # if your application is working properly.
                            #
                            # The readinessProbe is used to determine if
                            # an instance of your application can accept live
                            # requests. The configuration below tells Kubernetes
                            # to stop sending live requests to your application
                            # if it returns 3 non 2XX responses over 30 seconds.
                            # When this happens the application instance will
                            # be taken out of rotation and given time to "catch-up".
                            # Once it returns a single 2XX, Kubernetes will put
                            # it back in rotation.
                            #
                            # Kubernetes also has a livenessProbe that can be used to restart
                            # deadlocked processes. You can find out more about it here:
                            # https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-a-liveness-command
                            #
                            # We don't use a livenessProbe as it's easy to cause unnecessary
                            # restarts, which can be really disruptive to a site's availability.
                            # If you think your application is likely to be unstable after running
                            # for long periods send a note to reviz@allenai.org so we can work
                            # with you to craft the right livenessProbe.
                            readinessProbe: {
                                httpGet: apiHealthCheck + {
                                    path: '/health?check=rdy'
                                },
                                periodSeconds: 10,
                                failureThreshold: 3
                            },
                            startupProbe: {
                                httpGet: apiHealthCheck + {
                                    path: '/health?check=rdy'
                                },
                                periodSeconds: 10,
                                failureThreshold: 30,
                            },
                            # This tells Kubernetes what CPU and memory resources your API needs.
                            # We set these values low by default, as most applications receive
                            # bursts of activity and accordingly don't need dedicated resources
                            # at all times.
                            #
                            # Your application will be allowed to use more resources than what's
                            # specified below. But your application might be killed if it uses
                            # more than what's requested. If you know you need more memory
                            # or that your workload is CPU intensive, consider increasing the
                            # values below.
                            #
                            # For more information about these values, and the current maximums
                            # that your application can request, see:
                            # https://skiff.allenai.org/resources.html
                            resources: {
                                requests: {
                                    cpu: 4,
                                    memory: '1Gi'
                                },
                                limits: {
                                    cpu: 10,
                                    memory: '40Gi'
                                } + gpuLimits # only the first container should have gpuLimits applied
                            },
                            volumeMounts: [
                                {
                                    name: 'cfg',
                                    mountPath: '/secret/cfg',
                                    readOnly: true
                                },
                                {
                                    name: 'modal',
                                    mountPath: '/secret',
                                    readOnly: true
                                }
                            ]
                        }
                    ]
                }
            }
        }
    };

    local safetyWorkerHealthCheck = {
        port: 9191, // Prometheus endpoint
        scheme: 'HTTP'
    };

    local safetyWorkerSelectorLabels = {
        app: config.appName + '-safety-worker',
        env: env
    };

    local safetyWorkerFQN = fullyQualifiedName + '-safety-worker';
    local safetyWorkerPodLabels = podLabels + { app: config.appName + '-safety-worker', onlyOneOfPerNode: config.appName + '-safety-worker' + env };

    local numSafetyWorkerReplicas = if env == 'prod' then config.workerReplicas.prod else 1;

    local safetyWorkerDeployment = {
        apiVersion: 'apps/v1',
        kind: 'Deployment',
        metadata: {
            labels: labels,
            name: safetyWorkerFQN,
            namespace: namespaceName,
            annotations: annotations + {
                'kubernetes.io/change-cause': cause
            }
        },
        spec: {
            progressDeadlineSeconds: 3600, // 30 minutes, A100s are slow to scale up.
            strategy: {
                type: 'RollingUpdate',
                rollingUpdate: {
                    maxSurge: numSafetyWorkerReplicas // This makes deployments faster.
                }
            },
            revisionHistoryLimit: 3,
            replicas: numSafetyWorkerReplicas,
            selector: {
                matchLabels: safetyWorkerSelectorLabels
            },
            template: {
                metadata: {
                    name: safetyWorkerFQN,
                    namespace: namespaceName,
                    // It's OK if multiple workers get scheduled onto one node so we don't include anti-affinity labels here
                    labels: safetyWorkerPodLabels,
                    annotations: annotations
                },
                spec: {
                    nodeSelector: nodeSelector,
                    volumes: [
                        {
                            name: 'cfg',
                            secret: {
                                secretName: 'cfg'
                            }
                        },
                        {
                            name: 'modal',
                            secret: {
                                secretName: 'modal'
                            }
                        }
                    ],
                    containers: [
                        {
                            name: safetyWorkerFQN,
                            image: safetyWorkerImage,
                            env: [
                                {
                                    name: 'SHA',
                                    value: sha
                                },
                                {
                                    name: 'GOOGLE_APPLICATION_CREDENTIALS',
                                    value: '/secret/cfg/service_account.json'
                                },
                                {
                                    name: 'MODAL_CONFIG_PATH',
                                    value: '/secret/.modal.toml'
                                }
                            ],
                            # The "probes" below allow Kubernetes to determine
                            # if your application is working properly.
                            #
                            # The readinessProbe is used to determine if
                            # an instance of your application can accept live
                            # requests. The configuration below tells Kubernetes
                            # to stop sending live requests to your application
                            # if it returns 3 non 2XX responses over 30 seconds.
                            # When this happens the application instance will
                            # be taken out of rotation and given time to "catch-up".
                            # Once it returns a single 2XX, Kubernetes will put
                            # it back in rotation.
                            #
                            # Kubernetes also has a livenessProbe that can be used to restart
                            # deadlocked processes. You can find out more about it here:
                            # https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-a-liveness-command
                            #
                            # We don't use a livenessProbe as it's easy to cause unnecessary
                            # restarts, which can be really disruptive to a site's availability.
                            # If you think your application is likely to be unstable after running
                            # for long periods send a note to reviz@allenai.org so we can work
                            # with you to craft the right livenessProbe.
                            readinessProbe: {
                                httpGet: safetyWorkerHealthCheck,
                                periodSeconds: 10,
                                failureThreshold: 3
                            },
                            startupProbe: {
                                httpGet: safetyWorkerHealthCheck,
                                periodSeconds: 10,
                                failureThreshold: 30,
                            },
                            # This tells Kubernetes what CPU and memory resources your API needs.
                            # We set these values low by default, as most applications receive
                            # bursts of activity and accordingly don't need dedicated resources
                            # at all times.
                            #
                            # Your application will be allowed to use more resources than what's
                            # specified below. But your application might be killed if it uses
                            # more than what's requested. If you know you need more memory
                            # or that your workload is CPU intensive, consider increasing the
                            # values below.
                            #
                            # For more information about these values, and the current maximums
                            # that your application can request, see:
                            # https://skiff.allenai.org/resources.html
                            resources: {
                                requests: {
                                    cpu: 1,
                                    memory: '1Gi'
                                },
                                limits: {
                                    cpu: 4,
                                    memory: '2Gi'
                                } + gpuLimits # only the first container should have gpuLimits applied
                            },
                            volumeMounts: [
                                {
                                    name: 'cfg',
                                    mountPath: '/secret/cfg',
                                    readOnly: true
                                },
                                {
                                    name: 'modal',
                                    mountPath: '/secret',
                                    readOnly: true
                                }
                            ]
                        }
                    ]
                }
            }
        }
    };

    local flaskService = {
        apiVersion: 'v1',
        kind: 'Service',
        metadata: {
            name: fullyQualifiedName,
            namespace: namespaceName,
            labels: labels,
            annotations: annotations
        },
        spec: {
            selector: selectorLabels,
            ports: [
                {
                    port: apiPort,
                    name: 'http'
                }
            ]
        }
    };

    local flaskPdb = {
        apiVersion: 'policy/v1',
        kind: 'PodDisruptionBudget',
        metadata: {
            name: fullyQualifiedName,
            namespace: namespaceName,
            labels: labels,
        },
        spec: {
            minAvailable: if numReplicas > 1 then 1 else 0,
            selector: {
                matchLabels: selectorLabels,
            },
        },
    };

    local fastApiFQN = fullyQualifiedName + 'fastApi';

    local fastApiDeployment = {
        apiVersion: 'apps/v1',
        kind: 'Deployment',
        metadata: {
            labels: labels,
            name: fastApiFQN,
            namespace: namespaceName,
            annotations: annotations + {
                'kubernetes.io/change-cause': cause
            }
        },
        spec: {
            progressDeadlineSeconds: 3600, // 30 minutes, A100s are slow to scale up.
            strategy: {
                type: 'RollingUpdate',
                rollingUpdate: {
                    maxSurge: numReplicas // This makes deployments faster.
                }
            },
            revisionHistoryLimit: 3,
            replicas: numReplicas,
            selector: {
                matchLabels: selectorLabels
            },
            template: {
                metadata: {
                    name: fastApiFQN,
                    namespace: namespaceName,
                    labels: podLabels,
                    annotations: annotations
                },
                spec: {
                    # This block tells the cluster that we'd like to make sure
                    # each instance of your application is on a different node. This
                    # way if a node goes down, your application doesn't:
                    # See: https://kubernetes.io/docs/concepts/configuration/assign-pod-node/#node-isolation-restriction
                    affinity: {
                        podAntiAffinity: {
                            requiredDuringSchedulingIgnoredDuringExecution: [
                                {
                                   labelSelector: {
                                        matchExpressions: [
                                            {
                                                    key: labelName,
                                                    operator: 'In',
                                                    values: [ antiAffinityLabels[labelName], ],
                                            } for labelName in std.objectFields(antiAffinityLabels)
                                       ],
                                    },
                                    topologyKey: 'kubernetes.io/hostname'
                                },
                            ]
                        },
                    },
                    nodeSelector: nodeSelector,
                    volumes: [
                        {
                            name: 'cfg',
                            secret: {
                                secretName: 'cfg'
                            }
                        },
                        {
                            name: 'modal',
                            secret: {
                                secretName: 'modal'
                            }
                        }
                    ],
                    containers: [
                        {
                            name: fastApiFQN + '-api',
                            image: fastApiImage,
                            env: [
                                {
                                    name: 'SHA',
                                    value: sha
                                },
                                {
                                    name: 'GOOGLE_APPLICATION_CREDENTIALS',
                                    value: '/secret/cfg/service_account.json'
                                },
                                {
                                    name: 'MODAL_CONFIG_PATH',
                                    value: '/secret/.modal.toml'
                                }
                            ],
                            # The "probes" below allow Kubernetes to determine
                            # if your application is working properly.
                            #
                            # The readinessProbe is used to determine if
                            # an instance of your application can accept live
                            # requests. The configuration below tells Kubernetes
                            # to stop sending live requests to your application
                            # if it returns 3 non 2XX responses over 30 seconds.
                            # When this happens the application instance will
                            # be taken out of rotation and given time to "catch-up".
                            # Once it returns a single 2XX, Kubernetes will put
                            # it back in rotation.
                            #
                            # Kubernetes also has a livenessProbe that can be used to restart
                            # deadlocked processes. You can find out more about it here:
                            # https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-a-liveness-command
                            #
                            # We don't use a livenessProbe as it's easy to cause unnecessary
                            # restarts, which can be really disruptive to a site's availability.
                            # If you think your application is likely to be unstable after running
                            # for long periods send a note to reviz@allenai.org so we can work
                            # with you to craft the right livenessProbe.
                            readinessProbe: {
                                httpGet: apiHealthCheck + {
                                    path: '/health?check=rdy'
                                },
                                periodSeconds: 10,
                                failureThreshold: 3
                            },
                            startupProbe: {
                                httpGet: apiHealthCheck + {
                                    path: '/health?check=rdy'
                                },
                                periodSeconds: 10,
                                failureThreshold: 30,
                            },
                            # This tells Kubernetes what CPU and memory resources your API needs.
                            # We set these values low by default, as most applications receive
                            # bursts of activity and accordingly don't need dedicated resources
                            # at all times.
                            #
                            # Your application will be allowed to use more resources than what's
                            # specified below. But your application might be killed if it uses
                            # more than what's requested. If you know you need more memory
                            # or that your workload is CPU intensive, consider increasing the
                            # values below.
                            #
                            # For more information about these values, and the current maximums
                            # that your application can request, see:
                            # https://skiff.allenai.org/resources.html
                            resources: {
                                requests: {
                                    cpu: 2,
                                    memory: '1Gi'
                                },
                                limits: {
                                    cpu: 10,
                                    memory: '40Gi'
                                } + gpuLimits # only the first container should have gpuLimits applied
                            },
                            volumeMounts: [
                                {
                                    name: 'cfg',
                                    mountPath: '/secret/cfg',
                                    readOnly: true
                                },
                                {
                                    name: 'modal',
                                    mountPath: '/secret',
                                    readOnly: true
                                }
                            ]
                        }
                    ]
                }
            }
        }
    };


    local fastApiService = {
        apiVersion: 'v1',
        kind: 'Service',
        metadata: {
            name: fastApiFQN,
            namespace: namespaceName,
            labels: labels,
            annotations: annotations
        },
        spec: {
            selector: selectorLabels,
            ports: [
                {
                    port: apiPort,
                    name: 'http'
                }
            ]
        }
    };

    local fastApiPdb = {
        apiVersion: 'policy/v1',
        kind: 'PodDisruptionBudget',
        metadata: {
            name: fastApiFQN,
            namespace: namespaceName,
            labels: labels,
        },
        spec: {
            minAvailable: if numReplicas > 1 then 1 else 0,
            selector: {
                matchLabels: selectorLabels,
            },
        },
    };


    local defaultIngressAnno = {
        'nginx.ingress.kubernetes.io/ssl-redirect': 'true',
        'nginx.ingress.kubernetes.io/proxy-read-timeout': '120',
        'nginx.ingress.kubernetes.io/proxy-body-size': '100M'
    };

    local corsIngressAnno = {
        'nginx.ingress.kubernetes.io/enable-cors': 'true',
        'nginx.ingress.kubernetes.io/cors-allow-origin': 'https://olmo.allen.ai,https://*.olmo.allen.ai,https://playground.allenai.org,https://*.playground.allenai.org,https://*.olmo-ui.allen.ai,https://olmo-ui-playground-test.allen.ai',
        'nginx.ingress.kubernetes.io/cors-allow-credentials': 'true',
        'nginx.ingress.kubernetes.io/cors-allow-headers': 'DNT,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization,X-Anonymous-User-Id'
    };

    local ipsToDeny = [
        '3.228.45.243/32',
        '52.0.57.178/32',
        '44.209.54.138/32',
        '34.203.68.42/32',
        '54.237.110.6/32',
        '52.4.151.236/32',
        '44.212.146.219/32',
        '35.175.72.198/32',
        '34.230.254.100/32',
        '34.96.52.86/32',
        '185.220.101.0/24',
        '109.70.100.0/24'
    ];

    local ingressDenyAnno = {
            'nginx.ingress.kubernetes.io/server-snippet': std.join('; ', ['deny %s' % ip for ip in ipsToDeny]) + ';'
    };

    local allenAITLS = util.getTLSConfig(fullyQualifiedName + '-allen-dot-ai', allenAIHosts);
    local allenAIIngress = {
        apiVersion: 'networking.k8s.io/v1',
        kind: 'Ingress',
        metadata: {
            name: fullyQualifiedName + '-allen-dot-ai',
            namespace: namespaceName,
            labels: labels,
            annotations: annotations +
              allenAITLS.ingressAnnotations +
              defaultIngressAnno +
              corsIngressAnno +
              ingressDenyAnno
        },
        spec: {
            tls: [ allenAITLS.spec + { hosts: allenAIHosts } ],
            rules: [
                {
                    host: host,
                    http: {
                        paths: [
                            {
                                path: '/v5/',
                                pathType: 'Prefix',
                                backend: {
                                    service: {
                                        name: fastApiFQN,
                                        port: {
                                            number: apiPort
                                        }
                                    }
                                }
                            },
                            {
                                path: '/',
                                pathType: 'Prefix',
                                backend: {
                                    service: {
                                        name: fullyQualifiedName,
                                        port: {
                                            number: apiPort
                                        }
                                    }
                                }
                            }
                        ]
                    }
                } for host in allenAIHosts
            ]
        }
    };

    [
        namespace,
        allenAIIngress,
        flaskDeployment,
        safetyWorkerDeployment,
        flaskService,
        flaskPdb,
        fastApiDeployment,
        fastApiService,
        fastApiPdb
    ]
