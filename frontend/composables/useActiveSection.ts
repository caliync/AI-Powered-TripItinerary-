// Which of the given section ids is on screen, for highlighting its menu link.
export function useActiveSection(ids: string[]) {
  const active = ref('')
  let observer: IntersectionObserver | undefined

  function watchSections() {
    observer?.disconnect()
    observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting)
        if (visible.length) active.value = visible[0].target.id
      },
      { rootMargin: '-40% 0px -55% 0px' },
    )
    for (const id of ids) {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    }
  }

  const route = useRoute()
  onMounted(() => nextTick(watchSections))
  watch(() => route.path, () => { active.value = ''; nextTick(watchSections) })
  onBeforeUnmount(() => observer?.disconnect())
  return active
}
