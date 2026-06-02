// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    'introduction',
    {
      type: 'category',
      label: 'Deployment',
      link: { type: 'doc', id: 'get-started/index' },
      items: [
        'get-started/deploy',
        'get-started/architecture',
        'get-started/configuration_guide',
        'get-started/troubleshoot',
      ],
    },
    {
      type: 'category',
      label: 'User Guides',
      link: { type: 'doc', id: 'how-tos/index' },
      items: [
        'how-tos/use_pack_from_notebook',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      link: { type: 'doc', id: 'references/index' },
      items: [
        'references/values',
        'references/release_notes',
        'references/personas',
      ],
    },
  ],
};

module.exports = sidebars;
